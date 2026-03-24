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
        offset = "" if page_num <= 1 else f"_Desde_{(page_num - 1) * 48 + 1}"
        return (
            f"{BASE_URL}/venta/departamento/"
            f"{commune_slug}-metropolitana"
            f"_BEDROOMS_{bedrooms}-{bedrooms}"
            f"{offset}"
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

        # Múltiples selectores posibles (MercadoLibre cambia frecuentemente)
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
                    logger.debug(f"Encontrados {len(items)} items con selector: {selector}")
                    break
            except Exception:
                continue

        if not items:
            # Fallback: buscar todos los links de anuncio
            items = await page.query_selector_all("a[href*='/MLC-']")
            if items:
                logger.debug(f"Fallback: {len(items)} links de anuncio encontrados")
                return await self._parse_link_items(items, commune_name)

            logger.warning("No se encontraron resultados con ningún selector")
            return properties

        for item in items:
            try:
                prop = await self._parse_listing_item(item, commune_name)
                if prop:
                    properties.append(prop)
            except Exception as e:
                logger.debug(f"Error parseando item: {e}")
                continue

        return properties

    async def _parse_link_items(
        self, links: list, commune_name: str
    ) -> list[ScrapedProperty]:
        """Parsea items cuando solo tenemos los links de anuncio."""
        properties: list[ScrapedProperty] = []
        seen_ids: set[str] = set()

        for link in links:
            try:
                href = await link.get_attribute("href") or ""
                if "/MLC-" not in href:
                    continue

                source_id = self._extract_id_from_url(href)
                if source_id in seen_ids:
                    continue
                seen_ids.add(source_id)

                # Intentar obtener texto del contenedor padre
                parent = await link.evaluate_handle("el => el.closest('li') || el.closest('div') || el.parentElement")
                text = await parent.evaluate("el => el ? el.innerText : ''") if parent else ""

                title = text.split("\n")[0][:200] if text else source_id

                # Extraer precio del texto
                price_uf, price_clp = self._extract_price_from_text(text)

                # Extraer m² del texto
                m2_total = self._extract_m2_from_text(text)

                if title and source_id:
                    properties.append(ScrapedProperty(
                        source="portal_inmobiliario",
                        source_id=source_id,
                        source_url=href.split("?")[0],
                        title=title.strip(),
                        price_uf=price_uf,
                        price_clp=price_clp,
                        m2_total=m2_total,
                        commune=commune_name,
                    ))
            except Exception as e:
                logger.debug(f"Error parseando link: {e}")
                continue

        return properties

    async def _parse_listing_item(
        self, item, commune_name: str
    ) -> ScrapedProperty | None:
        """Parsea un item individual del listado."""
        # Título y URL — probar múltiples selectores
        source_url = ""
        title = ""

        for link_sel in ["a.ui-search-link", "a.poly-component__title", "a[href*='/MLC-']", "a"]:
            link_el = await item.query_selector(link_sel)
            if link_el:
                source_url = await link_el.get_attribute("href") or ""
                if "/MLC-" in source_url or "portalinmobiliario" in source_url:
                    break
                source_url = ""

        if not source_url:
            return None

        # Título
        for title_sel in ["h2", "h3", ".poly-component__title", ".ui-search-item__title", "a"]:
            title_el = await item.query_selector(title_sel)
            if title_el:
                title = (await title_el.inner_text()).strip()
                if title:
                    break

        if not title:
            return None

        source_id = self._extract_id_from_url(source_url)

        # Precio
        price_uf, price_clp = await self._parse_price(item)

        # Si no se encontró precio en elementos, buscar en texto completo
        if price_uf is None and price_clp is None:
            full_text = await item.inner_text()
            price_uf, price_clp = self._extract_price_from_text(full_text)

        # Atributos (m², dormitorios, baños)
        m2_total, bedrooms, bathrooms = await self._parse_attributes(item)

        # Si no se encontraron atributos, buscar en texto completo
        if m2_total is None:
            full_text = await item.inner_text()
            m2_total = self._extract_m2_from_text(full_text)

        # Dirección
        address = await self._parse_address(item)

        return ScrapedProperty(
            source="portal_inmobiliario",
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

    async def _parse_price(self, item) -> tuple[float | None, int | None]:
        """Extrae precio en UF y/o CLP."""
        price_uf = None
        price_clp = None

        # Probar múltiples selectores de precio
        for price_sel in [
            ".andes-money-amount__fraction",
            ".price-tag-fraction",
            ".poly-price__current .poly-component__price",
            "[class*='price'] [class*='fraction']",
            "[class*='Price']",
        ]:
            price_el = await item.query_selector(price_sel)
            if price_el:
                price_text = (await price_el.inner_text()).strip()
                price_text = price_text.replace(".", "").replace(",", ".").strip()

                # Buscar símbolo de moneda
                currency = ""
                for curr_sel in [".andes-money-amount__currency-symbol", ".price-tag-symbol", "[class*='currency']"]:
                    curr_el = await item.query_selector(curr_sel)
                    if curr_el:
                        currency = (await curr_el.inner_text()).strip()
                        break

                try:
                    value = float(price_text)
                    if "UF" in currency.upper():
                        price_uf = value
                    elif "$" in currency or value > 100000:
                        price_clp = int(value)
                    elif value < 10000:
                        price_uf = value
                except ValueError:
                    pass

                if price_uf is not None or price_clp is not None:
                    break

        return price_uf, price_clp

    async def _parse_attributes(
        self, item
    ) -> tuple[float | None, int | None, int | None]:
        """Extrae m², dormitorios y baños."""
        m2_total = None
        bedrooms = None
        bathrooms = None

        # Probar múltiples selectores
        for attr_sel in [
            ".ui-search-card-attributes__attribute",
            "[class*='attribute']",
            "li[class*='attr']",
            ".poly-attributes-list li",
        ]:
            attrs = await item.query_selector_all(attr_sel)
            if attrs:
                for attr in attrs:
                    text = (await attr.inner_text()).strip().lower()
                    m2_match = re.search(r"([\d,.]+)\s*m[²2]", text)
                    if m2_match:
                        m2_total = float(m2_match.group(1).replace(",", "."))
                    dorm_match = re.search(r"(\d+)\s*dorm", text)
                    if dorm_match:
                        bedrooms = int(dorm_match.group(1))
                    bath_match = re.search(r"(\d+)\s*baño", text)
                    if bath_match:
                        bathrooms = int(bath_match.group(1))
                break

        return m2_total, bedrooms, bathrooms

    async def _parse_address(self, item) -> str | None:
        """Extrae la dirección/ubicación."""
        for addr_sel in [
            ".ui-search-item__location",
            ".ui-search-item__group__element--location",
            "[class*='location']",
            "[class*='address']",
        ]:
            addr_el = await item.query_selector(addr_sel)
            if addr_el:
                return (await addr_el.inner_text()).strip()
        return None

    @staticmethod
    def _extract_id_from_url(url: str) -> str:
        """Extrae el ID del anuncio de la URL."""
        match = re.search(r"(MLC-?\d+)", url)
        if match:
            return match.group(1)
        return url.rstrip("/").split("/")[-1].split("?")[0]

    @staticmethod
    def _extract_price_from_text(text: str) -> tuple[float | None, int | None]:
        """Extrae precio de texto libre."""
        if not text:
            return None, None

        # UF
        uf_match = re.search(r"([\d.]+(?:,\d+)?)\s*UF", text, re.IGNORECASE)
        if uf_match:
            try:
                val = float(uf_match.group(1).replace(".", "").replace(",", "."))
                return val, None
            except ValueError:
                pass

        # CLP
        clp_match = re.search(r"\$\s*([\d.]+)", text)
        if clp_match:
            try:
                val = int(clp_match.group(1).replace(".", ""))
                if val > 500000:
                    return None, val
            except ValueError:
                pass

        return None, None

    @staticmethod
    def _extract_m2_from_text(text: str) -> float | None:
        """Extrae m² de texto libre."""
        if not text:
            return None
        m2_match = re.search(r"([\d,.]+)\s*m[²2]", text, re.IGNORECASE)
        if m2_match:
            try:
                return float(m2_match.group(1).replace(",", "."))
            except ValueError:
                pass
        return None
