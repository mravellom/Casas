import asyncio
import logging
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from playwright.async_api import Browser, Page, async_playwright

from app.config import settings

logger = logging.getLogger(__name__)

# Pool de User-Agents reales
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
    "Mozilla/5.0 (X11; Linux x86_64; rv:133.0) Gecko/20100101 Firefox/133.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
]


@dataclass
class ScrapedProperty:
    """Datos crudos de una propiedad scrapeada."""

    source: str
    source_id: str
    source_url: str
    title: str
    description: str | None = None
    price_uf: float | None = None
    price_clp: int | None = None
    m2_total: float | None = None
    m2_util: float | None = None
    bedrooms: int | None = None
    bathrooms: int | None = None
    commune: str = ""
    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    floor: int | None = None
    has_parking: bool | None = None
    has_bodega: bool | None = None
    building_year: int | None = None
    images: list[str] = field(default_factory=list)
    raw_data: dict = field(default_factory=dict)


class BaseScraper(ABC):
    """Clase base para scrapers con anti-bloqueo integrado."""

    def __init__(self):
        self.browser: Browser | None = None
        self.request_count: int = 0
        self.max_requests_per_session: int = settings.scraping_max_requests_per_session

    async def start(self):
        """Inicia el navegador Playwright."""
        self._playwright = await async_playwright().start()
        self.browser = await self._playwright.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        )
        logger.info(f"{self.__class__.__name__}: navegador iniciado")

    async def stop(self):
        """Cierra el navegador."""
        if self.browser:
            await self.browser.close()
        if self._playwright:
            await self._playwright.stop()
        logger.info(f"{self.__class__.__name__}: navegador cerrado")

    async def new_page(self) -> Page:
        """Crea una nueva página con User-Agent aleatorio."""
        ua = random.choice(USER_AGENTS)
        context = await self.browser.new_context(
            user_agent=ua,
            viewport={"width": 1920, "height": 1080},
            locale="es-CL",
            timezone_id="America/Santiago",
        )
        page = await context.new_page()

        # Bloquear recursos innecesarios para acelerar
        await page.route(
            "**/*.{png,jpg,jpeg,gif,svg,ico,woff,woff2,ttf}",
            lambda route: route.abort(),
        )

        return page

    async def random_delay(self):
        """Delay aleatorio entre requests para evitar detección."""
        delay = random.uniform(settings.scraping_delay_min, settings.scraping_delay_max)
        logger.debug(f"Esperando {delay:.1f}s...")
        await asyncio.sleep(delay)

    async def safe_goto(self, page: Page, url: str, retries: int = 3) -> bool:
        """Navega a una URL con reintentos y backoff."""
        for attempt in range(retries):
            try:
                self.request_count += 1
                if self.request_count > self.max_requests_per_session:
                    logger.warning("Límite de requests por sesión alcanzado")
                    return False

                response = await page.goto(url, wait_until="domcontentloaded", timeout=30000)

                if response and response.status == 429:
                    wait = (attempt + 1) * 10
                    logger.warning(f"Rate limited (429). Esperando {wait}s...")
                    await asyncio.sleep(wait)
                    continue

                if response and response.status >= 400:
                    logger.error(f"HTTP {response.status} en {url}")
                    return False

                return True

            except Exception as e:
                wait = (attempt + 1) * 5
                logger.error(f"Error navegando a {url} (intento {attempt + 1}): {e}")
                if attempt < retries - 1:
                    await asyncio.sleep(wait)

        return False

    @abstractmethod
    async def scrape(self) -> list[ScrapedProperty]:
        """Ejecuta el scraping y retorna propiedades encontradas."""
        ...

    @abstractmethod
    async def scrape_listing_page(self, page: Page, url: str) -> list[ScrapedProperty]:
        """Scrapea una página de listado."""
        ...
