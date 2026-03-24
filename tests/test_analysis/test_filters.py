import pytest

from app.analysis.filters import normalize_commune, normalize_price_text


class TestNormalizeCommune:
    def test_exact_match(self):
        assert normalize_commune("Santiago Centro") == "Santiago Centro"
        assert normalize_commune("San Miguel") == "San Miguel"
        assert normalize_commune("Ñuñoa") == "Ñuñoa"

    def test_lowercase(self):
        assert normalize_commune("santiago centro") == "Santiago Centro"
        assert normalize_commune("san miguel") == "San Miguel"
        assert normalize_commune("ñuñoa") == "Ñuñoa"

    def test_aliases(self):
        assert normalize_commune("stgo centro") == "Santiago Centro"
        assert normalize_commune("stgo") == "Santiago Centro"
        assert normalize_commune("est. central") == "Estación Central"
        assert normalize_commune("nunoa") == "Ñuñoa"

    def test_with_whitespace(self):
        assert normalize_commune("  Santiago Centro  ") == "Santiago Centro"
        assert normalize_commune(" san miguel ") == "San Miguel"

    def test_unknown_commune(self):
        assert normalize_commune("Providencia") is None
        assert normalize_commune("Las Condes") is None
        assert normalize_commune("") is None

    def test_partial_match(self):
        assert normalize_commune("estacion central") == "Estación Central"
        assert normalize_commune("estación central") == "Estación Central"


class TestNormalizePriceText:
    def test_uf_price(self):
        value, currency = normalize_price_text("2.500 UF")
        assert value == 2500.0
        assert currency == "UF"

    def test_uf_with_decimals(self):
        value, currency = normalize_price_text("2.350,50 UF")
        assert value == 2350.50
        assert currency == "UF"

    def test_clp_price(self):
        value, currency = normalize_price_text("$ 75.000.000")
        assert value == 75_000_000
        assert currency == "CLP"

    def test_empty(self):
        value, currency = normalize_price_text("")
        assert value is None
        assert currency == ""

    def test_no_price(self):
        value, currency = normalize_price_text("Consultar precio")
        assert value is None

    def test_uf_case_insensitive(self):
        value, currency = normalize_price_text("3000 uf")
        assert value == 3000.0
        assert currency == "UF"
