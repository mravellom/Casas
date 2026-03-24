import logging
import re

from playwright.async_api import Page

from app.scrapers.base import BaseScraper, ScrapedProperty

logger = logging.getLogger(__name__)

# Mapeo de comunas a slugs de URL en Portal Inmobiliario
COMMUNE_SLUGS = {
    "Santiago Centro": "santiago",
    "San Miguel": "san-miguel",
    "Estación Central": "estacion-central",
    "Ñuñoa": "nunoa",
}

BASE_URL = "https://www.portalinmobiliario.com"


class PortalInmobiliarioScraper(BaseScraper):
    """Scraper para portalinmobiliario.com (basado en MercadoLibre)."""

    def _build_search_url(self, commune_slug: str, bedrooms: int, page_num: int = 1) -> str:
        """Construye la URL de búsqueda filtrada."""
        # Portal Inmobiliario usa formato MercadoLibre
        # /venta/departamento/{dormitorios}-dormitorio/{comuna}-metropolitana
        dorms = f"{bedrooms}-dormitorio" if bedrooms == 1 else f"{bedrooms}-dormitorios"
        offset = "" if page_num <= 1 else f"_Desde_{(page_num - 1) * 48 + 1}"
        return (
            f"{BASE_URL}/venta/departamento/{dorms}/"
            f"{commune_slug}-metropolitana{offset}"
        )

    async def scrape(self) -> list[ScrapedProperty]:
        """Scrapea todas las comunas y tipos de dormitorio configurados."""
        all_properties: list[ScrapedProperty] = []

        await self.start()
        try:
            for commune_name, commune_slug in COMMUNE_SLUGS.items():
                for bedrooms in [1, 2]:
                    logger.info(
                        f"Scraping Portal Inmobiliario: {commune_name}, {bedrooms}d"
                    )
                    props = await self._scrape_commune(
                        commune_name, commune_slug, bedrooms
                    )
                    all_properties.extend(props)
                    await self.random_delay()
        finally:
            await self.stop()

        logger.info(
            f"Portal Inmobiliario: {len(all_properties)} propiedades encontradas"
        )
        return all_properties

    async def _scrape_commune(
        self, commune_name: str, commune_slug: str, bedrooms: int, max_pages: int = 3
    ) -> list[ScrapedProperty]:
        """Scrapea una comuna específica con paginación."""
        properties: list[ScrapedProperty] = []

        for page_num in range(1, max_pages + 1):
            url = self._build_search_url(commune_slug, bedrooms, page_num)
            page = await self.new_page()

            try:
                if not await self.safe_goto(page, url):
                    break

                page_props = await self.scrape_listing_page(page, commune_name)
                if not page_props:
                    logger.info(f"Sin resultados en página {page_num}, deteniendo")
                    break

                properties.extend(page_props)
                logger.info(
                    f"  Página {page_num}: {len(page_props)} propiedades"
                )

                await self.random_delay()
            finally:
                await page.context.close()

        return properties

    async def scrape_listing_page(
        self, page: Page, commune_name: str = ""
    ) -> list[ScrapedProperty]:
        """Parsea una página de resultados de Portal Inmobiliario."""
        properties: list[ScrapedProperty] = []

        try:
            # Esperar a que carguen los resultados
            await page.wait_for_selector(
                "li.ui-search-layout__item", timeout=15000
            )
        except Exception:
            logger.warning("No se encontraron resultados en la página")
            return properties

        items = await page.query_selector_all("li.ui-search-layout__item")

        for item in items:
            try:
                prop = await self._parse_listing_item(item, commune_name)
                if prop:
                    properties.append(prop)
            except Exception as e:
                logger.debug(f"Error parseando item: {e}")
                continue

        return properties

    async def _parse_listing_item(
        self, item, commune_name: str
    ) -> ScrapedProperty | None:
        """Parsea un item individual del listado."""
        # Título y URL
        link_el = await item.query_selector("a.ui-search-link")
        if not link_el:
            return None

        source_url = await link_el.get_attribute("href") or ""
        title_el = await item.query_selector(
            "h2.ui-search-item__title, .ui-search-item__group__element"
        )
        title = await title_el.inner_text() if title_el else ""

        if not source_url or not title:
            return None

        # Extraer source_id de la URL
        source_id = self._extract_id_from_url(source_url)

        # Precio
        price_uf, price_clp = await self._parse_price(item)

        # Atributos (m², dormitorios, baños)
        m2_total, bedrooms, bathrooms = await self._parse_attributes(item)

        # Dirección
        address = await self._parse_address(item)

        return ScrapedProperty(
            source="portal_inmobiliario",
            source_id=source_id,
            source_url=source_url.split("?")[0],  # Limpiar tracking params
            title=title.strip(),
            price_uf=price_uf,
            price_clp=price_clp,
            m2_total=m2_total,
            bedrooms=bedrooms,
            bathrooms=bathrooms,
            commune=commune_name,
            address=address,
        )

    async def _parse_price(self, item) -> tuple[float | None, int | None]:
        """Extrae precio en UF y/o CLP."""
        price_uf = None
        price_clp = None

        price_el = await item.query_selector(
            ".andes-money-amount__fraction, .price-tag-fraction"
        )
        currency_el = await item.query_selector(
            ".andes-money-amount__currency-symbol, .price-tag-symbol"
        )

        if price_el:
            price_text = await price_el.inner_text()
            price_text = price_text.replace(".", "").replace(",", ".").strip()

            currency = ""
            if currency_el:
                currency = (await currency_el.inner_text()).strip()

            try:
                value = float(price_text)
                if "UF" in currency.upper():
                    price_uf = value
                elif "$" in currency:
                    price_clp = int(value)
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

        attrs = await item.query_selector_all(
            ".ui-search-card-attributes__attribute"
        )
        for attr in attrs:
            text = (await attr.inner_text()).strip().lower()

            m2_match = re.search(r"([\d,.]+)\s*m²", text)
            if m2_match:
                m2_total = float(m2_match.group(1).replace(",", "."))

            dorm_match = re.search(r"(\d+)\s*dorm", text)
            if dorm_match:
                bedrooms = int(dorm_match.group(1))

            bath_match = re.search(r"(\d+)\s*baño", text)
            if bath_match:
                bathrooms = int(bath_match.group(1))

        return m2_total, bedrooms, bathrooms

    async def _parse_address(self, item) -> str | None:
        """Extrae la dirección/ubicación."""
        addr_el = await item.query_selector(
            ".ui-search-item__location, .ui-search-item__group__element--location"
        )
        if addr_el:
            return (await addr_el.inner_text()).strip()
        return None

    @staticmethod
    def _extract_id_from_url(url: str) -> str:
        """Extrae el ID del anuncio de la URL."""
        # Formato: MLC-123456789
        match = re.search(r"(MLC-?\d+)", url)
        if match:
            return match.group(1)
        # Fallback: usar parte final de la URL
        return url.rstrip("/").split("/")[-1].split("?")[0]
