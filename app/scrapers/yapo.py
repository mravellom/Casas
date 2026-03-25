"""Segundo scraper — búsqueda complementaria en Portal Inmobiliario.

Yapo.cl fue cerrado. ML Inmuebles, TocToc y Goplaceit no devuelven resultados.
Este scraper busca en Portal Inmobiliario con filtros diferentes al scraper
principal para maximizar la cobertura de propiedades individuales.

Estrategia: mientras el scraper principal busca por dormitorios específicos,
este busca por rango de precio UF para captar anuncios que el otro no ve.
"""
import logging
import re

from playwright.async_api import Page

from app.scrapers.base import BaseScraper, ScrapedProperty

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
    "title": "a.poly-component__title",
    "price_currency": ".andes-money-amount__currency-symbol",
    "price_fraction": ".andes-money-amount__fraction",
    "attributes": ".poly-attributes_list__item",
    "location": ".poly-component__location",
}


class ComplementaryScraper(BaseScraper):
    """Scraper complementario: busca por rango de precio en Portal Inmobiliario."""

    def _build_search_url(self, commune_slug: str, page_num: int = 1) -> str:
        """Busca deptos ordenados por más recientes, filtro por precio."""
        offset = "" if page_num <= 1 else f"_Desde_{(page_num - 1) * 48 + 1}"
        return (
            f"{BASE_URL}/venta/departamento/"
            f"{commune_slug}-metropolitana"
            f"_PriceRange_1500UF-4000UF"
            f"_OrderId_BEGINS*DESC"
            f"{offset}"
        )

    async def scrape(self) -> list[ScrapedProperty]:
        all_properties: list[ScrapedProperty] = []

        await self.start()
        try:
            for commune_name, commune_slug in COMMUNE_SLUGS.items():
                logger.info(f"Scraping complementario: {commune_name}")
                props = await self._scrape_commune(commune_name, commune_slug)
                all_properties.extend(props)
                await self.random_delay()
        finally:
            await self.stop()

        logger.info(f"Scraper complementario: {len(all_properties)} propiedades")
        return all_properties

    async def _scrape_commune(
        self, commune_name: str, commune_slug: str, max_pages: int = 2
    ) -> list[ScrapedProperty]:
        properties: list[ScrapedProperty] = []

        for page_num in range(1, max_pages + 1):
            url = self._build_search_url(commune_slug, page_num)
            page = await self.new_page()

            try:
                if not await self.safe_goto(page, url):
                    break

                page_props = await self.scrape_listing_page(page, commune_name)
                if not page_props:
                    logger.info(f"  Sin resultados en página {page_num}")
                    break

                properties.extend(page_props)
                logger.info(f"  Página {page_num}: {len(page_props)} propiedades")
                await self.random_delay()
            finally:
                await page.context.close()

        return properties

    async def scrape_listing_page(
        self, page: Page, commune_name: str = ""
    ) -> list[ScrapedProperty]:
        properties: list[ScrapedProperty] = []

        try:
            await page.wait_for_selector(SELECTORS["item"], timeout=15000)
        except Exception:
            logger.warning("Sin resultados en scraper complementario")
            return properties

        items = await page.query_selector_all(SELECTORS["item"])
        seen_ids: set[str] = set()

        for item in items:
            try:
                prop = await self._parse_item(item, commune_name)
                if prop and prop.source_id not in seen_ids:
                    seen_ids.add(prop.source_id)
                    properties.append(prop)
            except Exception as e:
                logger.debug(f"Error parseando item: {e}")

        return properties

    async def _parse_item(
        self, item, commune_name: str
    ) -> ScrapedProperty | None:
        title_el = await item.query_selector(SELECTORS["title"])
        if not title_el:
            return None

        title = (await title_el.inner_text()).strip()
        href = (await title_el.get_attribute("href")) or ""
        if not href:
            return None

        source_id = self._extract_id(href)
        if not source_id:
            return None

        # Precio
        price_uf, price_clp = await self._parse_price(item)

        # Atributos
        dorms, baths, m2 = await self._parse_attributes(item)

        # Ubicación
        loc_el = await item.query_selector(SELECTORS["location"])
        location = (await loc_el.inner_text()).strip() if loc_el else None

        clean_url = href.split("#")[0].split("?")[0]
        if not clean_url.startswith("http"):
            clean_url = f"https://portalinmobiliario.com{clean_url}"

        return ScrapedProperty(
            source="portal_inmobiliario",
            source_id=source_id,
            source_url=clean_url,
            title=title[:300],
            price_uf=price_uf,
            price_clp=price_clp,
            m2_total=m2,
            bedrooms=dorms,
            bathrooms=baths,
            commune=commune_name,
            address=location,
        )

    async def _parse_price(self, item) -> tuple[float | None, int | None]:
        fraction_el = await item.query_selector(SELECTORS["price_fraction"])
        currency_el = await item.query_selector(SELECTORS["price_currency"])

        if not fraction_el:
            return None, None

        fraction_text = (await fraction_el.inner_text()).strip()
        currency_text = (await currency_el.inner_text()).strip() if currency_el else ""

        try:
            clean = fraction_text.replace(".", "").replace(",", ".")
            value = float(clean)

            if "UF" in currency_text.upper():
                return value, None
            elif "$" in currency_text or value > 100000:
                return None, int(value)
            elif value < 50000:
                return value, None
        except ValueError:
            pass

        return None, None

    async def _parse_attributes(
        self, item
    ) -> tuple[int | None, int | None, float | None]:
        dorms = None
        baths = None
        m2 = None

        attr_els = await item.query_selector_all(SELECTORS["attributes"])
        for attr_el in attr_els:
            text = (await attr_el.inner_text()).strip().lower()

            if "dorm" in text or "estudio" in text:
                if "estudio" in text:
                    dorms = 1
                else:
                    match = re.search(r"(\d+)\s*(?:a\s+\d+\s+)?dorm", text)
                    if match:
                        dorms = int(match.group(1))

            elif "baño" in text:
                match = re.search(r"(\d+)\s*(?:a\s+\d+\s+)?baño", text)
                if match:
                    baths = int(match.group(1))

            elif "m²" in text or "m2" in text:
                match = re.search(r"([\d,.]+)\s*(?:-\s*[\d,.]+\s*)?m[²2]", text)
                if match:
                    try:
                        m2 = float(match.group(1).replace(",", "."))
                    except ValueError:
                        pass

        return dorms, baths, m2

    @staticmethod
    def _extract_id(url: str) -> str | None:
        match = re.search(r"(MLC-?\d+)", url)
        return match.group(1) if match else None


# Alias para compatibilidad con imports existentes
YapoScraper = ComplementaryScraper
MercadoLibreInmueblesScraper = ComplementaryScraper
