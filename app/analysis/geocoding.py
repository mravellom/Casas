"""Geocoding simple por comuna.

Asigna coordenadas aproximadas basadas en la comuna,
con dispersión aleatoria para que los marcadores no se apilen.
En futuro se puede integrar con API de geocoding real.
"""
import logging
import random
from datetime import datetime, timezone

from sqlalchemy import select, update

from app.database import async_session
from app.models.property import Property

logger = logging.getLogger(__name__)

# Centro de cada comuna con radio de dispersión (en grados, ~0.01 = ~1km)
COMMUNE_CENTERS = {
    "Santiago Centro": {"lat": -33.4420, "lng": -70.6530, "radius": 0.012},
    "San Miguel": {"lat": -33.4960, "lng": -70.6510, "radius": 0.008},
    "Estación Central": {"lat": -33.4570, "lng": -70.6850, "radius": 0.010},
    "Ñuñoa": {"lat": -33.4540, "lng": -70.6150, "radius": 0.012},
}


def _random_coord(center: float, radius: float) -> float:
    """Genera una coordenada aleatoria dentro del radio."""
    return center + random.uniform(-radius, radius)


async def geocode_properties() -> int:
    """Asigna coordenadas a propiedades que no las tienen, basándose en su comuna."""
    updated = 0

    async with async_session() as session:
        stmt = select(Property).where(
            Property.latitude.is_(None),
            Property.is_active.is_(True),
        )
        result = await session.execute(stmt)
        props = list(result.scalars().all())

        for prop in props:
            center = COMMUNE_CENTERS.get(prop.commune)
            if not center:
                continue

            prop.latitude = _random_coord(center["lat"], center["radius"])
            prop.longitude = _random_coord(center["lng"], center["radius"])
            prop.updated_at = datetime.now(timezone.utc)
            updated += 1

        await session.commit()

    if updated > 0:
        logger.info(f"Geocoding: {updated} propiedades geolocalizadas por comuna")

    return updated
