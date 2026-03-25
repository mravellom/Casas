from app.scrapers.portal_inmobiliario import PortalInmobiliarioScraper


class TestPortalInmobiliarioScraper:
    def setup_method(self):
        self.scraper = PortalInmobiliarioScraper()

    def test_build_search_url_1dorm_page1(self):
        url = self.scraper._build_search_url("santiago", 1, 1)
        assert "portalinmobiliario.com" in url
        assert "1-dormitorio" in url
        assert "santiago-metropolitana" in url
        assert "_Desde_" not in url

    def test_build_search_url_2dorms_page2(self):
        url = self.scraper._build_search_url("nunoa", 2, 2)
        assert "2-dormitorios" in url
        assert "nunoa-metropolitana" in url
        assert "_Desde_49" in url

    def test_build_search_url_page3(self):
        url = self.scraper._build_search_url("san-miguel", 1, 3)
        assert "_Desde_97" in url

    def test_extract_id_mlc_standard(self):
        result = PortalInmobiliarioScraper._extract_id(
            "https://portalinmobiliario.com/MLC-3625468226-abdon-cifuentes-_JM"
        )
        assert result == "MLC-3625468226"

    def test_extract_id_with_tracking(self):
        result = PortalInmobiliarioScraper._extract_id(
            "https://portalinmobiliario.com/MLC-99887766-depto#polycard_client=search"
        )
        assert result == "MLC-99887766"

    def test_extract_id_no_mlc(self):
        result = PortalInmobiliarioScraper._extract_id(
            "https://portalinmobiliario.com/venta/"
        )
        assert result is None
