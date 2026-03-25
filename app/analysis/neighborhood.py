"""Inteligencia de barrio usando Overpass API (OpenStreetMap).

Consulta servicios cercanos, metro actual, y calcula connectivity score.
Rate limited: máximo 1 request/segundo a Overpass API.
"""
import asyncio
import logging
from datetime import datetime, timezone

import httpx

from app.analysis.future_metro import find_nearest_future_station
from app.database import async_session
from app.models.property import Property
from sqlalchemy import select

logger = logging.getLogger(__name__)

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# Delay entre requests a Overpass (rate limit)
OVERPASS_DELAY = 1.5


async def _overpass_query(query: str) -> dict | None:
    """Ejecuta una query Overpass con timeout y manejo de errores."""
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(OVERPASS_URL, data={"data": query})
            response.raise_for_status()
            return response.json()
    except Exception as e:
        logger.debug(f"Overpass error: {e}")
        return None


async def get_nearest_metro(lat: float, lng: float) -> dict | None:
    """Busca la estación de Metro más cercana (radio 2km)."""
    query = f"""
    [out:json][timeout:10];
    (
      node["station"="subway"](around:2000,{lat},{lng});
      node["railway"="station"]["network"="Metro de Santiago"](around:2000,{lat},{lng});
    );
    out body 1;
    """
    data = await _overpass_query(query)
    if not data or not data.get("elements"):
        return None

    station = data["elements"][0]
    from app.analysis.future_metro import _haversine_meters
    distance = _haversine_meters(lat, lng, station["lat"], station["lon"])

    return {
        "name": station.get("tags", {}).get("name", "Metro"),
        "distance_m": round(distance),
        "walk_minutes": round(distance / 80),
    }


async def get_nearby_services(lat: float, lng: float, radius: int = 500) -> dict:
    """Cuenta servicios cercanos en un radio dado."""
    query = f"""
    [out:json][timeout:10];
    (
      node["shop"="supermarket"](around:{radius},{lat},{lng});
      node["amenity"="pharmacy"](around:{radius},{lat},{lng});
      node["leisure"="park"](around:{radius},{lat},{lng});
    );
    out body;
    """
    data = await _overpass_query(query)
    if not data:
        return {"supermarkets": 0, "pharmacies": 0, "parks": 0}

    counts = {"supermarkets": 0, "pharmacies": 0, "parks": 0}
    for el in data.get("elements", []):
        tags = el.get("tags", {})
        if tags.get("shop") == "supermarket":
            counts["supermarkets"] += 1
        elif tags.get("amenity") == "pharmacy":
            counts["pharmacies"] += 1
        elif tags.get("leisure") == "park":
            counts["parks"] += 1

    return counts


def calculate_connectivity_score(
    metro_distance_m: int | None,
    services: dict,
    future_metro: dict | None,
) -> int:
    """Calcula score de conectividad (0-100)."""
    score = 0

    # Metro actual (0-40 puntos)
    if metro_distance_m is not None:
        if metro_distance_m <= 300:
            score += 40
        elif metro_distance_m <= 500:
            score += 35
        elif metro_distance_m <= 800:
            score += 25
        elif metro_distance_m <= 1200:
            score += 15
        elif metro_distance_m <= 2000:
            score += 5

    # Servicios (0-30 puntos)
    score += min(services.get("supermarkets", 0) * 5, 15)
    score += min(services.get("pharmacies", 0) * 5, 10)
    score += min(services.get("parks", 0) * 5, 5)

    # Futuro metro (0-30 puntos)
    if future_metro:
        dist = future_metro["distance_m"]
        if dist <= 500:
            score += 30
        elif dist <= 800:
            score += 20
        elif dist <= 1500:
            score += 10

    return min(score, 100)


async def enrich_property_neighborhood(prop: Property) -> dict | None:
    """Enriquece una propiedad con datos de barrio."""
    if not prop.latitude or not prop.longitude:
        return None

    lat = float(prop.latitude)
    lng = float(prop.longitude)

    # Metro actual
    metro = await get_nearest_metro(lat, lng)
    await asyncio.sleep(OVERPASS_DELAY)

    # Servicios cercanos
    services = await get_nearby_services(lat, lng)
    await asyncio.sleep(OVERPASS_DELAY)

    # Metro futuro
    future = find_nearest_future_station(lat, lng)

    # Connectivity score
    conn_score = calculate_connectivity_score(
        metro["distance_m"] if metro else None,
        services,
        future,
    )

    return {
        "nearest_metro": metro,
        "services_500m": services,
        "future_metro": future,
        "connectivity_score": conn_score,
        "is_master_buy": future is not None and future["distance_m"] <= 800,
    }


async def enrich_all_properties(max_properties: int = 50):
    """Enriquece propiedades oportunidad con datos de barrio.

    Limitado a max_properties por ejecución para no saturar Overpass API.
    """
    logger.info("Enriqueciendo propiedades con datos de barrio...")
    enriched = 0

    async with async_session() as session:
        # Solo oportunidades sin datos de barrio
        stmt = (
            select(Property)
            .where(
                Property.is_active.is_(True),
                Property.is_opportunity.is_(True),
                Property.latitude.isnot(None),
            )
            .order_by(Property.opportunity_score.desc())
            .limit(max_properties)
        )
        result = await session.execute(stmt)

        for prop in result.scalars().all():
            # Verificar si ya tiene datos de barrio
            raw = prop.raw_data if isinstance(prop.raw_data, dict) else {}
            if raw.get("neighborhood"):
                continue

            data = await enrich_property_neighborhood(prop)
            if data:
                prop.raw_data = {**raw, "neighborhood": data}
                prop.updated_at = datetime.now(timezone.utc)
                enriched += 1
                logger.debug(
                    f"  {prop.commune}: metro={data['nearest_metro']}, "
                    f"conn={data['connectivity_score']}"
                )

        await session.commit()

    logger.info(f"Barrio: {enriched} propiedades enriquecidas")
    return enriched
