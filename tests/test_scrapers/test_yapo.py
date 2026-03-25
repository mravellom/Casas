from app.scrapers.yapo import ComplementaryScraper


class TestComplementaryScraper:
    def setup_method(self):
        self.scraper = ComplementaryScraper()

    def test_build_search_url_page1(self):
        url = self.scraper._build_search_url("santiago", 1)
        assert "portalinmobiliario.com" in url
        assert "santiago-metropolitana" in url
        assert "PriceRange" in url
        assert "_Desde_" not in url

    def test_build_search_url_page2(self):
        url = self.scraper._build_search_url("nunoa", 2)
        assert "nunoa-metropolitana" in url
        assert "_Desde_49" in url

    def test_extract_id_mlc(self):
        result = ComplementaryScraper._extract_id(
            "https://portalinmobiliario.com/MLC-3625468226-edificio"
        )
        assert result == "MLC-3625468226"

    def test_extract_id_none(self):
        result = ComplementaryScraper._extract_id(
            "https://portalinmobiliario.com/venta/"
        )
        assert result is None
