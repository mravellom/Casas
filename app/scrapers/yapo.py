import logging
import re

from playwright.async_api import Page

from app.scrapers.base import BaseScraper, ScrapedProperty

logger = logging.getLogger(__name__)

# Yapo.cl fue cerrado. Se reemplaza por Mercado Libre Inmuebles Chile.
# Mapeo de comunas a slugs de URL en inmuebles.mercadolibre.cl
COMMUNE_SLUGS = {
    "Santiago Centro": "santiago",
    "San Miguel": "san-miguel",
    "Estación Central": "estacion-central",
    "Ñuñoa": "nunoa",
}

BASE_URL = "https://inmuebles.mercadolibre.cl"


class MercadoLibreInmueblesScraper(BaseScraper):
    """Scraper para inmuebles.mercadolibre.cl (reemplazo de Yapo.cl)."""

    def _build_search_url(self, commune_slug: str, bedrooms: int, page_num: int = 1) -> str:
        """Construye la URL de búsqueda."""
        offset = "" if page_num <= 1 else f"_Desde_{(page_num - 1) * 48 + 1}"
        return (
            f"{BASE_URL}/venta/departamentos/"
            f"{commune_slug}-metropolitana"
            f"_BEDROOMS_{bedrooms}-{bedrooms}"
            f"{offset}"
        )

    async def scrape(self) -> list[ScrapedProperty]:
        """Scrapea todas las comunas configuradas."""
        all_properties: list[ScrapedProperty] = []

        await self.start()
        try:
            for commune_name, commune_slug in COMMUNE_SLUGS.items():
                for bedrooms in [1, 2]:
                    logger.info(
                        f"Scraping ML Inmuebles: {commune_name}, {bedrooms}d"
                    )
                    props = await self._scrape_commune(
                        commune_name, commune_slug, bedrooms
                    )
                    all_properties.extend(props)
                    await self.random_delay()
        finally:
            await self.stop()

        logger.info(f"ML Inmuebles: {len(all_properties)} propiedades encontradas")
        return all_properties

    async def _scrape_commune(
        self, commune_name: str, commune_slug: str, bedrooms: int, max_pages: int = 3
    ) -> list[ScrapedProperty]:
        """Scrapea una comuna con paginación."""
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
                logger.info(f"  Página {page_num}: {len(page_props)} propiedades")

                await self.random_delay()
            finally:
                await page.context.close()

        return properties

    async def scrape_listing_page(
        self, page: Page, commune_name: str = ""
    ) -> list[ScrapedProperty]:
        """Parsea una página de resultados de ML Inmuebles."""
        properties: list[ScrapedProperty] = []

        # ML Inmuebles usa los mismos selectores que MercadoLibre/Portal Inmobiliario
        selectors = [
            "li.ui-search-layout__item",
            "div.ui-search-result",
            "li[class*='ui-search']",
            "div.poly-card",
            "ol.ui-search-layout li",
        ]

        items = []
        for selector in selectors:
            try:
                await page.wait_for_selector(selector, timeout=10000)
                items = await page.query_selector_all(selector)
                if items:
                    break
            except Exception:
                continue

        if not items:
            # Fallback: links directos
            links = await page.query_selector_all("a[href*='/MLC-']")
            if links:
                return await self._parse_link_items(links, commune_name)
            logger.warning("No se encontraron resultados en ML Inmuebles")
            return properties

        for item in items:
            try:
                prop = await self._parse_listing_item(item, commune_name)
                if prop:
                    properties.append(prop)
            except Exception as e:
                logger.debug(f"Error parseando item ML: {e}")
                continue

        return properties

    async def _parse_link_items(
        self, links: list, commune_name: str
    ) -> list[ScrapedProperty]:
        """Parsea items desde links directos."""
        properties: list[ScrapedProperty] = []
        seen: set[str] = set()

        for link in links:
            try:
                href = await link.get_attribute("href") or ""
                if "/MLC-" not in href:
                    continue

                source_id = self._extract_id(href)
                if not source_id or source_id in seen:
                    continue
                seen.add(source_id)

                parent = await link.evaluate_handle(
                    "el => el.closest('li') || el.closest('div') || el.parentElement"
                )
                text = await parent.evaluate("el => el ? el.innerText : ''") if parent else ""
                title = text.split("\n")[0][:200] if text else source_id

                price_uf, price_clp = self._extract_price(text)
                m2_total = self._extract_m2(text)

                properties.append(ScrapedProperty(
                    source="mercadolibre_inmuebles",
                    source_id=source_id,
                    source_url=href.split("?")[0],
                    title=title.strip(),
                    price_uf=price_uf,
                    price_clp=price_clp,
                    m2_total=m2_total,
                    commune=commune_name,
                ))
            except Exception:
                continue

        return properties

    async def _parse_listing_item(
        self, item, commune_name: str
    ) -> ScrapedProperty | None:
        """Parsea un item individual del listado."""
        source_url = ""
        for sel in ["a.ui-search-link", "a.poly-component__title", "a[href*='/MLC-']", "a"]:
            el = await item.query_selector(sel)
            if el:
                source_url = await el.get_attribute("href") or ""
                if "/MLC-" in source_url:
                    break
                source_url = ""

        if not source_url:
            return None

        title = ""
        for sel in ["h2", "h3", ".poly-component__title", ".ui-search-item__title"]:
            el = await item.query_selector(sel)
            if el:
                title = (await el.inner_text()).strip()
                if title:
                    break

        if not title:
            return None

        source_id = self._extract_id(source_url)
        if not source_id:
            return None

        # Precio
        price_uf = None
        price_clp = None
        for sel in [".andes-money-amount__fraction", ".price-tag-fraction", "[class*='price'] [class*='fraction']"]:
            el = await item.query_selector(sel)
            if el:
                price_text = (await el.inner_text()).replace(".", "").replace(",", ".").strip()
                curr_el = await item.query_selector(".andes-money-amount__currency-symbol, [class*='currency']")
                currency = (await curr_el.inner_text()).strip() if curr_el else ""
                try:
                    value = float(price_text)
                    if "UF" in currency.upper():
                        price_uf = value
                    elif value > 100000:
                        price_clp = int(value)
                    elif value < 10000:
                        price_uf = value
                except ValueError:
                    pass
                break

        if price_uf is None and price_clp is None:
            text = await item.inner_text()
            price_uf, price_clp = self._extract_price(text)

        # Atributos
        m2_total = None
        bedrooms = None
        bathrooms = None
        for sel in [".ui-search-card-attributes__attribute", "[class*='attribute']", ".poly-attributes-list li"]:
            attrs = await item.query_selector_all(sel)
            if attrs:
                for attr in attrs:
                    text = (await attr.inner_text()).strip().lower()
                    m = re.search(r"([\d,.]+)\s*m[²2]", text)
                    if m:
                        m2_total = float(m.group(1).replace(",", "."))
                    m = re.search(r"(\d+)\s*dorm", text)
                    if m:
                        bedrooms = int(m.group(1))
                    m = re.search(r"(\d+)\s*baño", text)
                    if m:
                        bathrooms = int(m.group(1))
                break

        # Dirección
        address = None
        for sel in [".ui-search-item__location", "[class*='location']"]:
            el = await item.query_selector(sel)
            if el:
                address = (await el.inner_text()).strip()
                break

        return ScrapedProperty(
            source="mercadolibre_inmuebles",
            source_id=source_id,
            source_url=source_url.split("?")[0],
            title=title[:300],
            price_uf=price_uf,
            price_clp=price_clp,
            m2_total=m2_total,
            bedrooms=bedrooms,
            bathrooms=bathrooms,
            commune=commune_name,
            address=address,
        )

    @staticmethod
    def _extract_id(url: str) -> str | None:
        match = re.search(r"(MLC-?\d+)", url)
        if match:
            return match.group(1)
        return None

    @staticmethod
    def _extract_price(text: str) -> tuple[float | None, int | None]:
        if not text:
            return None, None
        uf = re.search(r"([\d.]+(?:,\d+)?)\s*UF", text, re.IGNORECASE)
        if uf:
            try:
                return float(uf.group(1).replace(".", "").replace(",", ".")), None
            except ValueError:
                pass
        clp = re.search(r"\$\s*([\d.]+)", text)
        if clp:
            try:
                val = int(clp.group(1).replace(".", ""))
                if val > 500000:
                    return None, val
            except ValueError:
                pass
        return None, None

    @staticmethod
    def _extract_m2(text: str) -> float | None:
        if not text:
            return None
        m = re.search(r"([\d,.]+)\s*m[²2]", text, re.IGNORECASE)
        if m:
            try:
                return float(m.group(1).replace(",", "."))
            except ValueError:
                pass
        return None


# Alias para compatibilidad con el worker
YapoScraper = MercadoLibreInmueblesScraper
