import logging
import re

from playwright.async_api import Page

from app.scrapers.base import BaseScraper, ScrapedProperty

logger = logging.getLogger(__name__)

# Mapeo de comunas a slugs de Yapo.cl
COMMUNE_SLUGS = {
    "Santiago Centro": "santiago",
    "San Miguel": "san_miguel",
    "Estación Central": "estacion_central",
    "Ñuñoa": "nunoa",
}

BASE_URL = "https://www.yapo.cl"


class YapoScraper(BaseScraper):
    """Scraper para yapo.cl — clasificados inmobiliarios."""

    def _build_search_url(self, commune_slug: str, page_num: int = 1) -> str:
        """Construye la URL de búsqueda en Yapo."""
        offset = "" if page_num <= 1 else f"&o={page_num}"
        return (
            f"{BASE_URL}/region_metropolitana/{commune_slug}/"
            f"venta_departamentos?ca=15{offset}"
        )

    async def scrape(self) -> list[ScrapedProperty]:
        """Scrapea todas las comunas configuradas."""
        all_properties: list[ScrapedProperty] = []

        await self.start()
        try:
            for commune_name, commune_slug in COMMUNE_SLUGS.items():
                logger.info(f"Scraping Yapo: {commune_name}")
                props = await self._scrape_commune(commune_name, commune_slug)
                all_properties.extend(props)
                await self.random_delay()
        finally:
            await self.stop()

        logger.info(f"Yapo: {len(all_properties)} propiedades encontradas")
        return all_properties

    async def _scrape_commune(
        self, commune_name: str, commune_slug: str, max_pages: int = 3
    ) -> list[ScrapedProperty]:
        """Scrapea una comuna con paginación."""
        properties: list[ScrapedProperty] = []

        for page_num in range(1, max_pages + 1):
            url = self._build_search_url(commune_slug, page_num)
            page = await self.new_page()

            try:
                if not await self.safe_goto(page, url):
                    break

                page_props = await self.scrape_listing_page(page, commune_name)
                if not page_props:
                    logger.info(f"Sin resultados en página {page_num}, deteniendo")
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
        """Parsea una página de resultados de Yapo."""
        properties: list[ScrapedProperty] = []

        try:
            # Yapo usa diferentes selectores según la versión
            await page.wait_for_selector(
                "[class*='listing'], [class*='ad-card'], .card-container",
                timeout=15000,
            )
        except Exception:
            logger.warning("No se encontraron resultados en Yapo")
            return properties

        # Intentar múltiples selectores (Yapo cambia frecuentemente)
        items = await page.query_selector_all(
            "[class*='ad-card'], .card-container, [data-ad-id]"
        )

        if not items:
            # Fallback: buscar links de anuncios
            items = await page.query_selector_all("a[href*='/venta_departamentos/']")

        for item in items:
            try:
                prop = await self._parse_listing_item(item, page, commune_name)
                if prop:
                    properties.append(prop)
            except Exception as e:
                logger.debug(f"Error parseando item Yapo: {e}")
                continue

        return properties

    async def _parse_listing_item(
        self, item, page: Page, commune_name: str
    ) -> ScrapedProperty | None:
        """Parsea un item individual de Yapo."""
        # Obtener URL del anuncio
        link_el = item if (await item.get_attribute("href")) else await item.query_selector("a")
        if not link_el:
            return None

        source_url = await link_el.get_attribute("href") or ""
        if not source_url:
            return None

        # Normalizar URL
        if source_url.startswith("/"):
            source_url = f"{BASE_URL}{source_url}"

        # Extraer ID
        source_id = self._extract_id(source_url)
        if not source_id:
            return None

        # Título
        title_el = await item.query_selector(
            "[class*='title'], h2, h3, .card-title"
        )
        title = ""
        if title_el:
            title = (await title_el.inner_text()).strip()
        if not title:
            title = (await item.inner_text()).strip()[:200]

        # Precio
        price_uf, price_clp = await self._parse_price(item)

        # Atributos
        m2_total, bedrooms, bathrooms = await self._parse_attributes(item)

        return ScrapedProperty(
            source="yapo",
            source_id=source_id,
            source_url=source_url.split("?")[0],
            title=title,
            price_uf=price_uf,
            price_clp=price_clp,
            m2_total=m2_total,
            bedrooms=bedrooms,
            bathrooms=bathrooms,
            commune=commune_name,
        )

    async def _parse_price(self, item) -> tuple[float | None, int | None]:
        """Extrae precio en UF y/o CLP de un item de Yapo."""
        price_uf = None
        price_clp = None

        price_el = await item.query_selector(
            "[class*='price'], .card-price, [class*='Price']"
        )
        if not price_el:
            return price_uf, price_clp

        price_text = (await price_el.inner_text()).strip()

        # Buscar precio en UF
        uf_match = re.search(r"([\d.,]+)\s*UF", price_text, re.IGNORECASE)
        if uf_match:
            try:
                price_uf = float(
                    uf_match.group(1).replace(".", "").replace(",", ".")
                )
            except ValueError:
                pass

        # Buscar precio en CLP
        clp_match = re.search(r"\$\s*([\d.,]+)", price_text)
        if clp_match and not uf_match:
            try:
                price_clp = int(
                    clp_match.group(1).replace(".", "").replace(",", "")
                )
            except ValueError:
                pass

        return price_uf, price_clp

    async def _parse_attributes(
        self, item
    ) -> tuple[float | None, int | None, int | None]:
        """Extrae m², dormitorios y baños."""
        m2_total = None
        bedrooms = None
        bathrooms = None

        full_text = (await item.inner_text()).lower()

        # Metros cuadrados
        m2_match = re.search(r"([\d,.]+)\s*m[²2]", full_text)
        if m2_match:
            try:
                m2_total = float(m2_match.group(1).replace(",", "."))
            except ValueError:
                pass

        # Dormitorios
        dorm_match = re.search(r"(\d+)\s*(?:dorm|hab|pieza)", full_text)
        if dorm_match:
            bedrooms = int(dorm_match.group(1))

        # Baños
        bath_match = re.search(r"(\d+)\s*baño", full_text)
        if bath_match:
            bathrooms = int(bath_match.group(1))

        return m2_total, bedrooms, bathrooms

    @staticmethod
    def _extract_id(url: str) -> str | None:
        """Extrae el ID del anuncio de la URL de Yapo."""
        # Formato típico: /.../_12345678
        match = re.search(r"_(\d+)(?:\?|$|\.)", url)
        if match:
            return match.group(1)
        # Fallback
        parts = url.rstrip("/").split("/")
        if parts:
            last = parts[-1].split("?")[0]
            id_match = re.search(r"(\d+)", last)
            if id_match:
                return id_match.group(1)
        return None
