import logging
import re
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import async_session
from app.models.market_average import MarketAverage
from app.models.property import Property

logger = logging.getLogger(__name__)

# Keywords que indican urgencia del vendedor
URGENCY_KEYWORDS = [
    "urgente",
    "urgencia",
    "remate",
    "conversable",
    "sin comisión",
    "sin comision",
    "liquidación",
    "liquidacion",
    "oportunidad",
    "bajo avalúo",
    "bajo avaluo",
    "precio rebajado",
    "rebajado",
    "necesito vender",
    "viaje",
    "apurado",
    "ganga",
    "oferta",
    "ocasión",
    "ocasion",
]

# Pesos del scoring según arquitectura
WEIGHTS = {
    "price_deviation": 0.40,
    "urgency_keywords": 0.20,
    "listing_age": 0.15,
    "completeness": 0.10,
    "extras": 0.10,
    "surface_bonus": 0.05,
}


def detect_urgency_keywords(title: str, description: str | None) -> list[str]:
    """Detecta keywords de urgencia en título y descripción.

    Retorna la lista de keywords encontradas.
    """
    text = (title or "").lower()
    if description:
        text += " " + description.lower()

    found = []
    for keyword in URGENCY_KEYWORDS:
        if keyword in text:
            found.append(keyword)

    return found


def calculate_score(
    prop: Property,
    avg_price_m2: float,
    median_price_m2: float | None = None,
) -> int:
    """Calcula el score de oportunidad (0-100) para una propiedad.

    Factores:
    - Desviación de precio vs zona (40%)
    - Keywords de urgencia (20%)
    - Antigüedad del aviso (15%)
    - Completitud de datos (10%)
    - Extras (parking/bodega) a precio bajo (10%)
    - Superficie vs promedio (5%)
    """
    scores = {}

    # 1. Desviación de precio vs zona (40%)
    scores["price_deviation"] = _score_price_deviation(prop, avg_price_m2)

    # 2. Keywords de urgencia (20%)
    scores["urgency_keywords"] = _score_urgency(prop)

    # 3. Antigüedad del aviso (15%)
    scores["listing_age"] = _score_age(prop)

    # 4. Completitud de datos (10%)
    scores["completeness"] = _score_completeness(prop)

    # 5. Extras (parking/bodega) (10%)
    scores["extras"] = _score_extras(prop, avg_price_m2)

    # 6. Superficie vs promedio (5%)
    scores["surface_bonus"] = _score_surface(prop)

    # Calcular score ponderado
    total = sum(
        scores[factor] * weight for factor, weight in WEIGHTS.items()
    )

    final_score = max(0, min(100, round(total)))
    return final_score


def _score_price_deviation(prop: Property, avg_price_m2: float) -> float:
    """Score basado en qué tan por debajo del promedio está (0-100)."""
    if not prop.price_m2_uf or avg_price_m2 <= 0:
        return 0

    deviation_pct = ((float(prop.price_m2_uf) - avg_price_m2) / avg_price_m2) * 100

    # Mapear desviación a score:
    # -30% o más bajo = 100
    # -15% = 60
    # 0% = 10
    # +10% o más = 0
    if deviation_pct <= -30:
        return 100
    elif deviation_pct <= -15:
        # Lineal de 60 a 100 entre -15% y -30%
        return 60 + ((-deviation_pct - 15) / 15) * 40
    elif deviation_pct <= 0:
        # Lineal de 10 a 60 entre 0% y -15%
        return 10 + (-deviation_pct / 15) * 50
    elif deviation_pct <= 10:
        # Lineal de 0 a 10 entre +10% y 0%
        return (10 - deviation_pct)
    else:
        return 0


def _score_urgency(prop: Property) -> float:
    """Score basado en keywords de urgencia encontradas (0-100)."""
    keywords = detect_urgency_keywords(prop.title, prop.description)

    if not keywords:
        return 0

    # Cada keyword suma puntos, máximo 100
    # 1 keyword = 40, 2 = 65, 3 = 80, 4+ = 100
    count = len(keywords)
    if count >= 4:
        return 100
    elif count == 3:
        return 80
    elif count == 2:
        return 65
    else:
        return 40


def _score_age(prop: Property) -> float:
    """Score basado en la antigüedad del aviso (0-100).

    Más nuevo = más puntos.
    """
    ref_time = prop.published_at or prop.first_seen_at
    if not ref_time:
        return 30  # Sin datos, score neutral

    now = datetime.now(timezone.utc)
    if ref_time.tzinfo is None:
        ref_time = ref_time.replace(tzinfo=timezone.utc)

    hours_old = (now - ref_time).total_seconds() / 3600

    # < 6 horas = 100
    # < 12 horas = 80
    # < 24 horas = 60
    # < 48 horas = 30
    # > 48 horas = 10
    if hours_old < 6:
        return 100
    elif hours_old < 12:
        return 80
    elif hours_old < 24:
        return 60
    elif hours_old < 48:
        return 30
    else:
        return 10


def _score_completeness(prop: Property) -> float:
    """Score basado en cuántos datos tiene la propiedad (0-100)."""
    total_fields = 12
    filled = 0

    if prop.description:
        filled += 1
    if prop.m2_total:
        filled += 1
    if prop.m2_util:
        filled += 1
    if prop.bedrooms is not None:
        filled += 1
    if prop.bathrooms is not None:
        filled += 1
    if prop.address:
        filled += 1
    if prop.latitude and prop.longitude:
        filled += 1
    if prop.floor is not None:
        filled += 1
    if prop.has_parking is not None:
        filled += 1
    if prop.has_bodega is not None:
        filled += 1
    if prop.building_year is not None:
        filled += 1
    if prop.images:
        filled += 1

    return (filled / total_fields) * 100


def _score_extras(prop: Property, avg_price_m2: float) -> float:
    """Score por tener extras (parking/bodega) a precio bajo (0-100)."""
    if not prop.price_m2_uf or avg_price_m2 <= 0:
        return 0

    deviation_pct = ((float(prop.price_m2_uf) - avg_price_m2) / avg_price_m2) * 100

    # Solo da puntos si está bajo el promedio
    if deviation_pct >= 0:
        return 0

    score = 0
    if prop.has_parking:
        score += 50
    if prop.has_bodega:
        score += 50

    return score


def _score_surface(prop: Property) -> float:
    """Bonus si la superficie es mayor al promedio de su tipo (0-100).

    Promedio aproximado para Santiago:
    - 1 dorm: ~35-40 m²
    - 2 dorm: ~50-55 m²
    """
    if not prop.m2_total or not prop.bedrooms:
        return 0

    avg_m2 = {1: 38, 2: 52}
    expected = avg_m2.get(prop.bedrooms, 45)

    excess_pct = ((float(prop.m2_total) - expected) / expected) * 100

    if excess_pct >= 30:
        return 100
    elif excess_pct >= 15:
        return 70
    elif excess_pct >= 5:
        return 40
    elif excess_pct >= 0:
        return 20
    else:
        return 0


async def score_all_properties():
    """Calcula el score de todas las propiedades activas sin score.

    Requiere que los promedios de mercado estén calculados.
    """
    logger.info("Calculando scores de oportunidad...")
    scored = 0
    opportunities = 0

    async with async_session() as session:
        # Cargar promedios de mercado
        avg_stmt = select(MarketAverage)
        avg_result = await session.execute(avg_stmt)
        averages = {
            (ma.commune, ma.bedrooms): ma for ma in avg_result.scalars().all()
        }

        if not averages:
            missing = [c for c in settings.target_communes if not any(
                k[0] == c for k in averages
            )]
            logger.warning(
                f"No hay promedios de mercado. Comunas sin datos: {missing or 'todas'}"
            )
            return 0, 0

        # Batch processing para evitar OOM con datasets grandes
        BATCH_SIZE = 500
        offset = 0
        skipped_no_avg = 0

        while True:
            stmt = (
                select(Property)
                .where(
                    Property.is_active.is_(True),
                    Property.price_m2_uf.isnot(None),
                    Property.price_m2_uf > 0,
                )
                .offset(offset)
                .limit(BATCH_SIZE)
            )
            result = await session.execute(stmt)
            properties = list(result.scalars().all())

            if not properties:
                break

            for prop in properties:
                key = (prop.commune, prop.bedrooms)
                market_avg = averages.get(key)
                if not market_avg:
                    skipped_no_avg += 1
                    continue

                avg_m2 = float(market_avg.avg_price_m2_uf)
                median_m2 = (
                    float(market_avg.median_price_m2_uf)
                    if market_avg.median_price_m2_uf
                    else None
                )

                keywords = detect_urgency_keywords(prop.title, prop.description)
                prop.has_urgency_keyword = len(keywords) > 0

                score = calculate_score(prop, avg_m2, median_m2)
                prop.opportunity_score = score

                deviation_pct = (
                    (float(prop.price_m2_uf) - avg_m2) / avg_m2
                ) * 100

                is_opp = (
                    deviation_pct <= settings.price_deviation_threshold
                    or (prop.has_urgency_keyword and deviation_pct <= -10)
                )
                prop.is_opportunity = is_opp

                scored += 1
                if is_opp:
                    opportunities += 1

            await session.commit()
            offset += BATCH_SIZE

        if skipped_no_avg > 0:
            logger.warning(f"Propiedades sin promedio de zona: {skipped_no_avg}")

    logger.info(
        f"Scoring completado: {scored} propiedades analizadas, "
        f"{opportunities} oportunidades detectadas"
    )
    return scored, opportunities
