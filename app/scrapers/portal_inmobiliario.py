import logging
import re

from playwright.async_api import Page

from app.scrapers.base import BaseScraper, ScrapedProperty

logger = logging.getLogger(__name__)

# Comunas objetivo con sus slugs en la URL
COMMUNE_SLUGS = {
    "Santiago Centro": "santiago",
    "San Miguel": "san-miguel",
    "Estación Central": "estacion-central",
    "Ñuñoa": "nunoa",
}

BASE_URL = "https://www.portalinmobiliario.com"

# Selectores CSS verificados contra el HTML real (marzo 2026)
# Estructura: poly-card dentro de ui-search-layout__item
SELECTORS = {
    "item": "li.ui-search-layout__item",
    "title": "a.poly-component__title",
    "price_currency": ".andes-money-amount__currency-symbol",
    "price_fraction": ".andes-money-amount__fraction",
    "attributes": ".poly-attributes_list__item",
    "location": ".poly-component__location",
    "headline": ".poly-component__headline",
}


class PortalInmobiliarioScraper(BaseScraper):
    """Scraper para portalinmobiliario.com (MercadoLibre Chile).

    Estructura HTML verificada: poly-card con andes-money-amount.
    """

    def _build_search_url(self, commune_slug: str, bedrooms: int, page_num: int = 1) -> str:
        dorms = f"{bedrooms}-dormitorio" if bedrooms == 1 else f"{bedrooms}-dormitorios"
        offset = "" if page_num <= 1 else f"_Desde_{(page_num - 1) * 48 + 1}"
        return f"{BASE_URL}/venta/departamento/{dorms}/{commune_slug}-metropolitana{offset}"

    async def scrape(self) -> list[ScrapedProperty]:
        all_properties: list[ScrapedProperty] = []

        await self.start()
        try:
            for commune_name, commune_slug in COMMUNE_SLUGS.items():
                for bedrooms in [1, 2]:
                    logger.info(f"Scraping PI: {commune_name}, {bedrooms}d")
                    props = await self._scrape_commune(commune_name, commune_slug, bedrooms)
                    all_properties.extend(props)
                    await self.random_delay()
        finally:
            await self.stop()

        logger.info(f"Portal Inmobiliario: {len(all_properties)} propiedades")
        return all_properties

    async def _scrape_commune(
        self, commune_name: str, commune_slug: str, bedrooms: int, max_pages: int = 3
    ) -> list[ScrapedProperty]:
        properties: list[ScrapedProperty] = []

        for page_num in range(1, max_pages + 1):
            url = self._build_search_url(commune_slug, bedrooms, page_num)
            page = await self.new_page()

            try:
                if not await self.safe_goto(page, url):
                    break

                page_props = await self.scrape_listing_page(page, commune_name, bedrooms)
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
        self, page: Page, commune_name: str = "", bedrooms: int | None = None
    ) -> list[ScrapedProperty]:
        properties: list[ScrapedProperty] = []

        try:
            await page.wait_for_selector(SELECTORS["item"], timeout=15000)
        except Exception:
            logger.warning("No se encontraron resultados")
            return properties

        items = await page.query_selector_all(SELECTORS["item"])
        seen_ids: set[str] = set()

        for item in items:
            try:
                prop = await self._parse_item(item, commune_name, bedrooms)
                if prop and prop.source_id not in seen_ids:
                    seen_ids.add(prop.source_id)
                    properties.append(prop)
            except Exception as e:
                logger.debug(f"Error parseando item: {e}")

        return properties

    async def _parse_item(
        self, item, commune_name: str, bedrooms: int | None
    ) -> ScrapedProperty | None:
        # Título y link
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

        # Atributos (dormitorios, baños, m²)
        dorms, baths, m2 = await self._parse_attributes(item)

        # Si no se pudo extraer dormitorios del HTML, usar el del filtro
        if dorms is None and bedrooms is not None:
            dorms = bedrooms

        # Ubicación
        location = await self._parse_location(item)

        # Limpiar URL de tracking params
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
        """Extrae precio. Formato verificado: UF 3.152"""
        price_uf = None
        price_clp = None

        fraction_el = await item.query_selector(SELECTORS["price_fraction"])
        currency_el = await item.query_selector(SELECTORS["price_currency"])

        if not fraction_el:
            return None, None

        fraction_text = (await fraction_el.inner_text()).strip()
        currency_text = (await currency_el.inner_text()).strip() if currency_el else ""

        # Limpiar: "3.152" → 3152.0 o "3.152,50" → 3152.50
        try:
            clean = fraction_text.replace(".", "").replace(",", ".")
            value = float(clean)

            if "UF" in currency_text.upper():
                price_uf = value
            elif "$" in currency_text or value > 100000:
                price_clp = int(value)
            elif value < 50000:
                # Probablemente UF si es un número pequeño
                price_uf = value
        except ValueError:
            pass

        return price_uf, price_clp

    async def _parse_attributes(
        self, item
    ) -> tuple[int | None, int | None, float | None]:
        """Extrae dormitorios, baños y m² de los atributos.

        Formatos encontrados:
        - "2 dormitorios"
        - "1 a 2 dormitorios" (rango, tomar el menor)
        - "Estudio a 2 dormitorios"
        - "1 a 2 baños"
        - "32 - 49 m² útiles" (rango, tomar el menor)
        - "45 m² útiles"
        """
        dorms = None
        baths = None
        m2 = None

        attr_els = await item.query_selector_all(SELECTORS["attributes"])

        for attr_el in attr_els:
            text = (await attr_el.inner_text()).strip().lower()

            # Dormitorios
            if "dorm" in text or "estudio" in text:
                if "estudio" in text:
                    dorms = 1  # Estudio = 1 dormitorio
                else:
                    # "2 dormitorios" o "1 a 2 dormitorios"
                    match = re.search(r"(\d+)\s*(?:a\s+\d+\s+)?dorm", text)
                    if match:
                        dorms = int(match.group(1))

            # Baños
            elif "baño" in text:
                match = re.search(r"(\d+)\s*(?:a\s+\d+\s+)?baño", text)
                if match:
                    baths = int(match.group(1))

            # Metros cuadrados
            elif "m²" in text or "m2" in text:
                # "32 - 49 m² útiles" → tomar primer número
                match = re.search(r"([\d,.]+)\s*(?:-\s*[\d,.]+\s*)?m[²2]", text)
                if match:
                    try:
                        m2 = float(match.group(1).replace(",", "."))
                    except ValueError:
                        pass

        return dorms, baths, m2

    async def _parse_location(self, item) -> str | None:
        """Extrae ubicación. Formato: 'Calle 123, Comuna, Barrio, Ciudad'"""
        loc_el = await item.query_selector(SELECTORS["location"])
        if loc_el:
            return (await loc_el.inner_text()).strip()
        return None

    @staticmethod
    def _extract_id(url: str) -> str | None:
        match = re.search(r"(MLC-?\d+)", url)
        return match.group(1) if match else None
