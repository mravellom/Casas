import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

from app.notifications.telegram import format_opportunity_alert


def _make_property(**kwargs):
    """Crea un mock de Property para tests."""
    defaults = {
        "id": uuid.uuid4(),
        "source": "portal_inmobiliario",
        "source_id": "MLC-123",
        "source_url": "https://www.portalinmobiliario.com/MLC-123",
        "title": "Depto 2D 1B Santiago Centro",
        "description": "Lindo departamento",
        "price_uf": 2350.0,
        "price_clp": None,
        "price_m2_uf": 52.2,
        "m2_total": 45.0,
        "m2_util": None,
        "bedrooms": 1,
        "bathrooms": 1,
        "commune": "Santiago Centro",
        "address": "Calle Test 123",
        "has_parking": True,
        "has_bodega": False,
        "opportunity_score": 87,
        "has_urgency_keyword": True,
        "is_opportunity": True,
        "is_active": True,
        "first_seen_at": datetime.now(timezone.utc),
        "published_at": None,
    }
    defaults.update(kwargs)
    prop = MagicMock()
    for key, value in defaults.items():
        setattr(prop, key, value)
    return prop


class TestFormatOpportunityAlert:
    def test_gold_opportunity(self):
        prop = _make_property(opportunity_score=87)
        msg = format_opportunity_alert(prop, avg_price_m2=64.4)

        assert "ORO" in msg
        assert "87" in msg
        assert "Santiago Centro" in msg
        assert "2,350 UF" in msg
        assert "portalinmobiliario.com" in msg

    def test_silver_opportunity(self):
        prop = _make_property(opportunity_score=65)
        msg = format_opportunity_alert(prop, avg_price_m2=60.0)

        assert "PLATA" in msg
        assert "65" in msg

    def test_bronze_opportunity(self):
        prop = _make_property(opportunity_score=45)
        msg = format_opportunity_alert(prop, avg_price_m2=55.0)

        assert "BRONCE" in msg

    def test_pct_below_market(self):
        # price_m2_uf=52.2, avg=64.4 → ~-18.9%
        prop = _make_property(price_m2_uf=52.2)
        msg = format_opportunity_alert(prop, avg_price_m2=64.4)

        assert "vs mercado" in msg

    def test_no_avg_price(self):
        prop = _make_property()
        msg = format_opportunity_alert(prop, avg_price_m2=None)

        # No debería fallar sin promedio
        assert "Santiago Centro" in msg
        assert "UF" in msg

    def test_parking_shown(self):
        prop = _make_property(has_parking=True)
        msg = format_opportunity_alert(prop, avg_price_m2=60.0)

        assert "Estacionamiento: Si" in msg

    def test_no_parking(self):
        prop = _make_property(has_parking=False)
        msg = format_opportunity_alert(prop, avg_price_m2=60.0)

        assert "Estacionamiento: No" in msg

    def test_urgency_keyword_shown(self):
        prop = _make_property(has_urgency_keyword=True)
        msg = format_opportunity_alert(prop, avg_price_m2=60.0)

        assert "urgencia" in msg.lower()

    def test_contains_link(self):
        prop = _make_property(
            source_url="https://www.portalinmobiliario.com/MLC-999"
        )
        msg = format_opportunity_alert(prop, avg_price_m2=60.0)

        assert "https://www.portalinmobiliario.com/MLC-999" in msg

    def test_estimated_market_value(self):
        # avg_m2=64.4, m2=45 → estimated = 2,898 UF
        prop = _make_property(price_m2_uf=52.2, m2_total=45.0)
        msg = format_opportunity_alert(prop, avg_price_m2=64.4)

        assert "Valor mercado" in msg

    def test_no_price_m2(self):
        prop = _make_property(price_m2_uf=None, m2_total=None)
        msg = format_opportunity_alert(prop, avg_price_m2=64.4)

        # No debería fallar
        assert "Santiago Centro" in msg
