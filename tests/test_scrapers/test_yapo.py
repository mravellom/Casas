from app.scrapers.yapo import YapoScraper


class TestYapoScraper:
    """Tests unitarios para el scraper de Yapo."""

    def setup_method(self):
        self.scraper = YapoScraper()

    def test_build_search_url_page1(self):
        url = self.scraper._build_search_url("santiago", 1)
        assert "yapo.cl" in url
        assert "santiago" in url
        assert "venta_departamentos" in url
        assert "&o=" not in url

    def test_build_search_url_page2(self):
        url = self.scraper._build_search_url("nunoa", 2)
        assert "&o=2" in url

    def test_extract_id_standard(self):
        url = "https://www.yapo.cl/region_metropolitana/venta_departamentos/_12345678"
        result = YapoScraper._extract_id(url)
        assert result == "12345678"

    def test_extract_id_with_extension(self):
        url = "https://www.yapo.cl/algo/_99887766.html"
        result = YapoScraper._extract_id(url)
        assert result == "99887766"

    def test_extract_id_none(self):
        url = "https://www.yapo.cl/region_metropolitana/"
        result = YapoScraper._extract_id(url)
        assert result is None
