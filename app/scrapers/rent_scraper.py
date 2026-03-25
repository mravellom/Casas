"""Scraper de arriendos en Portal Inmobiliario.

Extrae precios de arriendo para calcular rentabilidad.
Se ejecuta 1 vez por semana (no necesita frecuencia alta).
"""
import logging
import re
from datetime import datetime, timezone

import numpy as np
from playwright.async_api import Page
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.database import async_session
from app.models.rent_average import RentAverage
from app.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

COMMUNE_SLUGS = {
    "Santiago Centro": "santiago",
    "San Miguel": "san-miguel",
    "Estación Central": "estacion-central",
    "Ñuñoa": "nunoa",
}

BASE_URL = "https://www.portalinmobiliario.com"

SELECTORS = {
    "item": "li.ui-search-layout__item",
    "price_currency": ".andes-money-amount__currency-symbol",
    "price_fraction": ".andes-money-amount__fraction",
    "attributes": ".poly-attributes_list__item",
}


class RentScraper(BaseScraper):
    """Scrapea arriendos para calcular rentabilidad."""

    def _build_url(self, commune_slug: str, bedrooms: int) -> str:
        dorms = f"{bedrooms}-dormitorio" if bedrooms == 1 else f"{bedrooms}-dormitorios"
        return f"{BASE_URL}/arriendo/departamento/{dorms}/{commune_slug}-metropolitana"

    async def scrape_and_save(self) -> int:
        """Scrapea arriendos y guarda promedios en BD."""
        logger.info("=== Scraping de arriendos ===")
        zones_updated = 0

        await self.start()
        try:
            for commune_name, commune_slug in COMMUNE_SLUGS.items():
                for bedrooms in [1, 2]:
                    rents = await self._scrape_rents(commune_slug, bedrooms)
                    if len(rents) >= 3:
                        await self._save_average(commune_name, bedrooms, rents)
                        zones_updated += 1
                        logger.info(
                            f"  {commune_name} {bedrooms}d: "
                            f"avg={np.mean(rents):.2f} UF/mes (n={len(rents)})"
                        )
                    else:
                        logger.warning(
                            f"  {commune_name} {bedrooms}d: solo {len(rents)} arriendos"
                        )
                    await self.random_delay()
        finally:
            await self.stop()

        logger.info(f"Arriendos: {zones_updated} zonas actualizadas")
        return zones_updated

    async def _scrape_rents(
        self, commune_slug: str, bedrooms: int
    ) -> list[float]:
        """Extrae precios de arriendo de una página."""
        rents: list[float] = []
        url = self._build_url(commune_slug, bedrooms)
        page = await self.new_page()

        try:
            if not await self.safe_goto(page, url):
                return rents

            try:
                await page.wait_for_selector(SELECTORS["item"], timeout=15000)
            except Exception:
                return rents

            items = await page.query_selector_all(SELECTORS["item"])

            for item in items:
                price_uf = await self._extract_rent_price(item)
                if price_uf and 3 <= price_uf <= 50:  # Rango razonable de arriendo
                    rents.append(price_uf)
        finally:
            await page.context.close()

        return rents

    async def _extract_rent_price(self, item) -> float | None:
        """Extrae precio de arriendo en UF."""
        fraction_el = await item.query_selector(SELECTORS["price_fraction"])
        currency_el = await item.query_selector(SELECTORS["price_currency"])

        if not fraction_el:
            return None

        fraction = (await fraction_el.inner_text()).strip()
        currency = (await currency_el.inner_text()).strip() if currency_el else ""

        try:
            value = float(fraction.replace(".", "").replace(",", "."))
            if "UF" in currency.upper():
                return value
            # Si está en CLP, convertir (arriendo típico: 300k-1.5M CLP)
            if value > 100000:
                return value / 38000  # Aprox UF
        except ValueError:
            pass

        return None

    async def _save_average(
        self, commune: str, bedrooms: int, rents: list[float]
    ):
        """Guarda promedio de arriendo con upsert atómico."""
        arr = np.array(rents)
        now = datetime.now(timezone.utc)

        # Eliminar outliers con IQR
        q1, q3 = np.percentile(arr, [25, 75])
        iqr = q3 - q1
        filtered = arr[(arr >= q1 - 1.5 * iqr) & (arr <= q3 + 1.5 * iqr)]
        if len(filtered) < 3:
            filtered = arr

        async with async_session() as session:
            stmt = pg_insert(RentAverage).values(
                commune=commune,
                bedrooms=bedrooms,
                avg_rent_uf=float(np.mean(filtered)),
                median_rent_uf=float(np.median(filtered)),
                min_rent_uf=float(np.min(filtered)),
                max_rent_uf=float(np.max(filtered)),
                sample_count=len(filtered),
                last_updated=now,
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=["commune", "bedrooms"],
                set_={
                    "avg_rent_uf": stmt.excluded.avg_rent_uf,
                    "median_rent_uf": stmt.excluded.median_rent_uf,
                    "min_rent_uf": stmt.excluded.min_rent_uf,
                    "max_rent_uf": stmt.excluded.max_rent_uf,
                    "sample_count": stmt.excluded.sample_count,
                    "last_updated": now,
                },
            )
            await session.execute(stmt)
            await session.commit()

    # Required by BaseScraper ABC
    async def scrape(self):
        return []

    async def scrape_listing_page(self, page, url=""):
        return []
