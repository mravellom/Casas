from app.scrapers.base import ScrapedProperty, USER_AGENTS


class TestScrapedProperty:
    """Tests para el dataclass ScrapedProperty."""

    def test_create_minimal(self):
        prop = ScrapedProperty(
            source="portal_inmobiliario",
            source_id="MLC-12345",
            source_url="https://example.com/12345",
            title="Depto 2D 1B Santiago Centro",
        )
        assert prop.source == "portal_inmobiliario"
        assert prop.source_id == "MLC-12345"
        assert prop.price_uf is None
        assert prop.images == []
        assert prop.raw_data == {}

    def test_create_full(self):
        prop = ScrapedProperty(
            source="yapo",
            source_id="99887766",
            source_url="https://yapo.cl/99887766",
            title="Departamento 1 dormitorio Ñuñoa",
            price_uf=2500.0,
            m2_total=45.0,
            bedrooms=1,
            bathrooms=1,
            commune="Ñuñoa",
            address="Av. Irarrázaval 1234",
        )
        assert prop.price_uf == 2500.0
        assert prop.m2_total == 45.0
        assert prop.commune == "Ñuñoa"

    def test_price_m2_calculation(self):
        prop = ScrapedProperty(
            source="test",
            source_id="1",
            source_url="http://test.com/1",
            title="Test",
            price_uf=2500.0,
            m2_total=50.0,
        )
        price_m2 = prop.price_uf / prop.m2_total
        assert price_m2 == 50.0


class TestUserAgents:
    """Tests para el pool de User-Agents."""

    def test_has_agents(self):
        assert len(USER_AGENTS) >= 5

    def test_agents_are_realistic(self):
        for ua in USER_AGENTS:
            assert "Mozilla" in ua
            assert len(ua) > 50
