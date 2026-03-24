import pytest

from app.analysis.uf_converter import clp_to_uf, clear_cache, uf_to_clp


class TestUFConversion:
    """Tests para conversión UF <-> CLP."""

    def test_clp_to_uf(self):
        # UF ~38,000 CLP (valor aproximado)
        uf_value = 38000.0
        result = clp_to_uf(76_000_000, uf_value)
        assert result == 2000.0

    def test_uf_to_clp(self):
        uf_value = 38000.0
        result = uf_to_clp(2000.0, uf_value)
        assert result == 76_000_000

    def test_clp_to_uf_rounding(self):
        uf_value = 38000.0
        result = clp_to_uf(100_000_000, uf_value)
        assert result == 2631.58

    def test_invalid_uf_value_raises(self):
        with pytest.raises(ValueError):
            clp_to_uf(1000, 0)

        with pytest.raises(ValueError):
            uf_to_clp(1.0, -1)

    def test_clp_to_uf_small_amount(self):
        uf_value = 38000.0
        result = clp_to_uf(38000, uf_value)
        assert result == 1.0

    def test_round_trip(self):
        """Convertir CLP -> UF -> CLP debe dar ~el mismo valor."""
        uf_value = 37_800.50
        original_clp = 75_000_000
        uf = clp_to_uf(original_clp, uf_value)
        back_to_clp = uf_to_clp(uf, uf_value)
        # Diferencia aceptable por redondeo
        assert abs(back_to_clp - original_clp) < 50_000
