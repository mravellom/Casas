from app.scrapers.yapo import MercadoLibreInmueblesScraper


class TestMercadoLibreInmueblesScraper:
    """Tests para el scraper de ML Inmuebles (reemplazo de Yapo.cl)."""

    def setup_method(self):
        self.scraper = MercadoLibreInmueblesScraper()

    def test_build_search_url_page1(self):
        url = self.scraper._build_search_url("santiago", 1, 1)
        assert "inmuebles.mercadolibre.cl" in url
        assert "santiago-metropolitana" in url
        assert "_BEDROOMS_1-1" in url
        assert "_Desde_" not in url

    def test_build_search_url_page2(self):
        url = self.scraper._build_search_url("nunoa", 2, 2)
        assert "nunoa-metropolitana" in url
        assert "_Desde_49" in url

    def test_extract_id_mlc(self):
        url = "https://inmuebles.mercadolibre.cl/MLC-12345678"
        result = MercadoLibreInmueblesScraper._extract_id(url)
        assert result == "MLC-12345678"

    def test_extract_id_with_params(self):
        url = "https://inmuebles.mercadolibre.cl/MLC-99887766?tracking=abc"
        result = MercadoLibreInmueblesScraper._extract_id(url)
        assert result == "MLC-99887766"

    def test_extract_id_none(self):
        url = "https://inmuebles.mercadolibre.cl/venta/"
        result = MercadoLibreInmueblesScraper._extract_id(url)
        assert result is None

    def test_extract_price_uf(self):
        price_uf, price_clp = MercadoLibreInmueblesScraper._extract_price("2.350 UF depto")
        assert price_uf == 2350.0

    def test_extract_price_clp(self):
        price_uf, price_clp = MercadoLibreInmueblesScraper._extract_price("$ 80.000.000")
        assert price_clp == 80000000

    def test_extract_m2(self):
        m2 = MercadoLibreInmueblesScraper._extract_m2("Depto 45 m² 2 dormitorios")
        assert m2 == 45.0
