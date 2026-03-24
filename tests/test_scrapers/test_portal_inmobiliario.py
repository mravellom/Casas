from app.scrapers.portal_inmobiliario import PortalInmobiliarioScraper


class TestPortalInmobiliarioScraper:
    """Tests unitarios para el scraper de Portal Inmobiliario."""

    def setup_method(self):
        self.scraper = PortalInmobiliarioScraper()

    def test_build_search_url_page1(self):
        url = self.scraper._build_search_url("santiago", 1, 1)
        assert "portalinmobiliario.com" in url
        assert "1-dormitorio" in url
        assert "santiago-metropolitana" in url
        assert "_Desde_" not in url

    def test_build_search_url_page2(self):
        url = self.scraper._build_search_url("nunoa", 2, 2)
        assert "2-dormitorios" in url
        assert "nunoa-metropolitana" in url
        assert "_Desde_49" in url

    def test_build_search_url_page3(self):
        url = self.scraper._build_search_url("san-miguel", 1, 3)
        assert "_Desde_97" in url

    def test_extract_id_from_url_mlc(self):
        url = "https://www.portalinmobiliario.com/MLC-12345678-depto"
        result = PortalInmobiliarioScraper._extract_id_from_url(url)
        assert result == "MLC-12345678"

    def test_extract_id_from_url_with_params(self):
        url = "https://www.portalinmobiliario.com/MLC-99887766-depto?tracking=abc"
        result = PortalInmobiliarioScraper._extract_id_from_url(url)
        assert result == "MLC-99887766"

    def test_extract_id_fallback(self):
        url = "https://www.portalinmobiliario.com/some-listing-id"
        result = PortalInmobiliarioScraper._extract_id_from_url(url)
        assert result == "some-listing-id"
