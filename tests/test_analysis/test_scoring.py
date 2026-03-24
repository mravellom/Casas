import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from app.analysis.scoring import (
    URGENCY_KEYWORDS,
    _score_age,
    _score_completeness,
    _score_extras,
    _score_price_deviation,
    _score_surface,
    _score_urgency,
    calculate_score,
    detect_urgency_keywords,
)


def _make_property(**kwargs):
    """Crea un mock de Property para tests."""
    defaults = {
        "id": uuid.uuid4(),
        "source": "test",
        "source_id": "1",
        "title": "Depto test",
        "description": None,
        "price_uf": 2500.0,
        "price_m2_uf": 50.0,
        "m2_total": 50.0,
        "m2_util": None,
        "bedrooms": 2,
        "bathrooms": 1,
        "commune": "Santiago Centro",
        "address": "Test 123",
        "latitude": None,
        "longitude": None,
        "floor": None,
        "has_parking": None,
        "has_bodega": None,
        "building_year": None,
        "images": None,
        "first_seen_at": datetime.now(timezone.utc),
        "published_at": None,
        "is_opportunity": False,
        "opportunity_score": None,
        "has_urgency_keyword": False,
    }
    defaults.update(kwargs)
    prop = MagicMock()
    for key, value in defaults.items():
        setattr(prop, key, value)
    return prop


class TestDetectUrgencyKeywords:
    def test_no_keywords(self):
        result = detect_urgency_keywords("Depto 2D 1B Ñuñoa", "Lindo departamento")
        assert result == []

    def test_single_keyword_title(self):
        result = detect_urgency_keywords("URGENTE vendo depto", None)
        assert "urgente" in result

    def test_multiple_keywords(self):
        result = detect_urgency_keywords(
            "Remate urgente", "Precio conversable, sin comisión"
        )
        assert "remate" in result
        assert "urgente" in result
        assert "conversable" in result
        assert "sin comisión" in result

    def test_case_insensitive(self):
        result = detect_urgency_keywords("LIQUIDACIÓN TOTAL", None)
        assert "liquidación" in result

    def test_keyword_in_description_only(self):
        result = detect_urgency_keywords("Depto bonito", "necesito vender por viaje")
        assert "necesito vender" in result
        assert "viaje" in result

    def test_all_keywords_exist(self):
        """Verifica que la lista de keywords no está vacía."""
        assert len(URGENCY_KEYWORDS) >= 10


class TestScorePriceDeviation:
    def test_30pct_below(self):
        prop = _make_property(price_m2_uf=35.0)
        score = _score_price_deviation(prop, avg_price_m2=50.0)
        assert score == 100  # -30% = max score

    def test_15pct_below(self):
        prop = _make_property(price_m2_uf=42.5)
        score = _score_price_deviation(prop, avg_price_m2=50.0)
        assert score == 60  # -15% = 60

    def test_at_average(self):
        prop = _make_property(price_m2_uf=50.0)
        score = _score_price_deviation(prop, avg_price_m2=50.0)
        assert score == 10  # 0% = 10

    def test_above_average(self):
        prop = _make_property(price_m2_uf=60.0)
        score = _score_price_deviation(prop, avg_price_m2=50.0)
        assert score == 0  # +20% = 0

    def test_no_price(self):
        prop = _make_property(price_m2_uf=None)
        score = _score_price_deviation(prop, avg_price_m2=50.0)
        assert score == 0


class TestScoreUrgency:
    def test_no_keywords(self):
        prop = _make_property(title="Depto normal", description=None)
        score = _score_urgency(prop)
        assert score == 0

    def test_one_keyword(self):
        prop = _make_property(title="Depto urgente", description=None)
        score = _score_urgency(prop)
        assert score == 40

    def test_two_keywords(self):
        prop = _make_property(title="Remate urgente", description=None)
        score = _score_urgency(prop)
        assert score == 65

    def test_four_keywords(self):
        prop = _make_property(
            title="Remate urgente",
            description="Conversable, sin comisión",
        )
        score = _score_urgency(prop)
        assert score == 100


class TestScoreAge:
    def test_very_new(self):
        prop = _make_property(
            first_seen_at=datetime.now(timezone.utc) - timedelta(hours=2),
            published_at=None,
        )
        score = _score_age(prop)
        assert score == 100

    def test_12_hours(self):
        prop = _make_property(
            first_seen_at=datetime.now(timezone.utc) - timedelta(hours=10),
            published_at=None,
        )
        score = _score_age(prop)
        assert score == 80

    def test_24_hours(self):
        prop = _make_property(
            first_seen_at=datetime.now(timezone.utc) - timedelta(hours=20),
            published_at=None,
        )
        score = _score_age(prop)
        assert score == 60

    def test_old(self):
        prop = _make_property(
            first_seen_at=datetime.now(timezone.utc) - timedelta(days=5),
            published_at=None,
        )
        score = _score_age(prop)
        assert score == 10


class TestScoreCompleteness:
    def test_minimal_data(self):
        prop = _make_property(
            description=None,
            m2_total=None,
            m2_util=None,
            bedrooms=None,
            bathrooms=None,
            address=None,
            latitude=None,
            longitude=None,
            floor=None,
            has_parking=None,
            has_bodega=None,
            building_year=None,
            images=None,
        )
        score = _score_completeness(prop)
        assert score == 0

    def test_full_data(self):
        prop = _make_property(
            description="Desc",
            m2_total=50,
            m2_util=45,
            bedrooms=2,
            bathrooms=1,
            address="Test 123",
            latitude=-33.4,
            longitude=-70.6,
            floor=5,
            has_parking=True,
            has_bodega=True,
            building_year=2020,
            images=["img1.jpg"],
        )
        score = _score_completeness(prop)
        assert score == 100


class TestScoreExtras:
    def test_parking_and_bodega_below_avg(self):
        prop = _make_property(
            price_m2_uf=40.0, has_parking=True, has_bodega=True
        )
        score = _score_extras(prop, avg_price_m2=50.0)
        assert score == 100

    def test_parking_only_below_avg(self):
        prop = _make_property(price_m2_uf=40.0, has_parking=True, has_bodega=None)
        score = _score_extras(prop, avg_price_m2=50.0)
        assert score == 50

    def test_extras_above_avg(self):
        prop = _make_property(price_m2_uf=55.0, has_parking=True, has_bodega=True)
        score = _score_extras(prop, avg_price_m2=50.0)
        assert score == 0  # Por encima del promedio, no cuenta


class TestScoreSurface:
    def test_large_1_bedroom(self):
        prop = _make_property(m2_total=55.0, bedrooms=1)  # avg 38m²
        score = _score_surface(prop)
        assert score >= 70  # +44% sobre promedio

    def test_average_2_bedroom(self):
        prop = _make_property(m2_total=52.0, bedrooms=2)  # avg 52m²
        score = _score_surface(prop)
        assert score == 20  # justo en promedio

    def test_small(self):
        prop = _make_property(m2_total=30.0, bedrooms=1)  # bajo promedio
        score = _score_surface(prop)
        assert score == 0


class TestCalculateScore:
    def test_excellent_opportunity(self):
        """Propiedad muy por debajo del mercado, con keywords, nueva."""
        prop = _make_property(
            title="URGENTE remate depto",
            description="Precio conversable",
            price_m2_uf=30.0,
            m2_total=50.0,
            bedrooms=2,
            has_parking=True,
            has_bodega=True,
            first_seen_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        score = calculate_score(prop, avg_price_m2=50.0)
        assert score >= 80  # Debería ser Oportunidad Oro

    def test_average_property(self):
        """Propiedad al precio promedio, sin keywords."""
        prop = _make_property(
            title="Depto 2D 1B",
            price_m2_uf=50.0,
            m2_total=52.0,
            bedrooms=2,
            first_seen_at=datetime.now(timezone.utc) - timedelta(days=3),
        )
        score = calculate_score(prop, avg_price_m2=50.0)
        assert score < 40  # Debería ser descartada

    def test_overpriced(self):
        """Propiedad por encima del mercado."""
        prop = _make_property(
            title="Depto premium",
            price_m2_uf=70.0,
            m2_total=50.0,
            bedrooms=2,
            first_seen_at=datetime.now(timezone.utc) - timedelta(days=5),
        )
        score = calculate_score(prop, avg_price_m2=50.0)
        assert score < 20

    def test_score_bounds(self):
        """Score siempre entre 0 y 100."""
        prop = _make_property(price_m2_uf=10.0)
        score = calculate_score(prop, avg_price_m2=50.0)
        assert 0 <= score <= 100

        prop2 = _make_property(price_m2_uf=200.0)
        score2 = calculate_score(prop2, avg_price_m2=50.0)
        assert 0 <= score2 <= 100
