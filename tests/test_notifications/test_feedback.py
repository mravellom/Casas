import uuid
from unittest.mock import MagicMock

from app.notifications.telegram import format_opportunity_alert


class TestFeedbackFormat:
    """Tests para verificar que el formato de alerta incluye info necesaria para feedback."""

    def _make_property(self, **kwargs):
        defaults = {
            "id": uuid.uuid4(),
            "source": "portal_inmobiliario",
            "source_id": "MLC-456",
            "source_url": "https://www.portalinmobiliario.com/MLC-456",
            "title": "Depto 1D urgente",
            "description": "Necesito vender",
            "price_uf": 1800.0,
            "price_clp": None,
            "price_m2_uf": 45.0,
            "m2_total": 40.0,
            "m2_util": None,
            "bedrooms": 1,
            "bathrooms": 1,
            "commune": "Ñuñoa",
            "address": "Av. Irarrázaval 1234",
            "has_parking": False,
            "has_bodega": None,
            "opportunity_score": 82,
            "has_urgency_keyword": True,
            "is_opportunity": True,
            "is_active": True,
        }
        defaults.update(kwargs)
        prop = MagicMock()
        for key, value in defaults.items():
            setattr(prop, key, value)
        return prop

    def test_alert_has_all_feedback_info(self):
        """El mensaje de alerta debe tener suficiente info para que el usuario
        pueda evaluar si la oportunidad es real."""
        prop = self._make_property()
        msg = format_opportunity_alert(prop, avg_price_m2=55.0)

        # Información esencial para evaluar
        assert "Ñuñoa" in msg                    # Comuna
        assert "1,800 UF" in msg                  # Precio
        assert "vs mercado" in msg                # Comparación
        assert "45.0 UF/m²" in msg                # Precio por m²
        assert "40 m²" in msg                     # Superficie
        assert "portalinmobiliario.com" in msg    # Link

    def test_alert_shows_urgency_flag(self):
        prop = self._make_property(has_urgency_keyword=True)
        msg = format_opportunity_alert(prop, avg_price_m2=55.0)
        assert "urgencia" in msg.lower()

    def test_alert_shows_estimated_value(self):
        """Debe mostrar valor estimado de mercado para comparar."""
        prop = self._make_property(price_m2_uf=45.0, m2_total=40.0)
        msg = format_opportunity_alert(prop, avg_price_m2=55.0)
        # 55.0 * 40 = 2,200 UF
        assert "Valor mercado" in msg
