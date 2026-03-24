import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update

from app.database import async_session
from app.models.property import Property

logger = logging.getLogger(__name__)

STALE_HOURS = 48  # Propiedades no vistas en 48h se marcan inactivas


async def mark_stale_properties() -> int:
    """Marca como inactivas las propiedades no vistas en las últimas 48 horas.

    Las propiedades inactivas no aparecen en búsquedas ni generan alertas,
    pero se conservan en la BD para historial.
    """
    threshold = datetime.now(timezone.utc) - timedelta(hours=STALE_HOURS)

    async with async_session() as session:
        stmt = (
            update(Property)
            .where(
                Property.is_active == True,  # noqa: E712
                Property.last_seen_at < threshold,
            )
            .values(is_active=False, updated_at=datetime.now(timezone.utc))
        )
        result = await session.execute(stmt)
        count = result.rowcount
        await session.commit()

    if count > 0:
        logger.info(f"Limpieza: {count} propiedades marcadas como inactivas (>{STALE_HOURS}h sin verse)")

    return count


async def get_stale_stats() -> dict:
    """Estadísticas de propiedades activas vs inactivas."""
    async with async_session() as session:
        active_stmt = (
            select(Property)
            .where(Property.is_active == True)  # noqa: E712
        )
        active_result = await session.execute(active_stmt)
        active_count = len(active_result.all())

        inactive_stmt = (
            select(Property)
            .where(Property.is_active == False)  # noqa: E712
        )
        inactive_result = await session.execute(inactive_stmt)
        inactive_count = len(inactive_result.all())

    return {
        "active": active_count,
        "inactive": inactive_count,
        "total": active_count + inactive_count,
        "stale_threshold_hours": STALE_HOURS,
    }
