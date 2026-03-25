"""Detección de calidad de avisos.

Identifica avisos de dueños directos, detecta avisos sospechosos,
y gestiona auto-ocultamiento por feedback negativo.
"""
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, update

from app.database import async_session
from app.models.feedback import Feedback
from app.models.property import Property

logger = logging.getLogger(__name__)

DIRECT_OWNER_KEYWORDS = [
    "dueño vende",
    "dueño directo",
    "sin comisión",
    "sin comision",
    "sin corredor",
    "directo",
    "propietario vende",
    "propietario directo",
    "particular vende",
    "no corredor",
]

SUSPICIOUS_KEYWORDS = [
    "llame ahora",
    "solo hoy",
    "últimas unidades",
    "no se lo pierda",
]


def detect_direct_owner(title: str, description: str | None) -> bool:
    """Detecta si el aviso es de un dueño directo (no corredor)."""
    text = (title or "").lower()
    if description:
        text += " " + description.lower()

    return any(kw in text for kw in DIRECT_OWNER_KEYWORDS)


def detect_suspicious(title: str, description: str | None) -> list[str]:
    """Detecta señales sospechosas en un aviso."""
    text = (title or "").lower()
    if description:
        text += " " + description.lower()

    return [kw for kw in SUSPICIOUS_KEYWORDS if kw in text]


async def classify_all_listings():
    """Clasifica todas las propiedades activas como dueño directo o no."""
    logger.info("Clasificando avisos...")
    direct = 0

    async with async_session() as session:
        stmt = select(Property).where(Property.is_active.is_(True))
        result = await session.execute(stmt)

        for prop in result.scalars().all():
            is_direct = detect_direct_owner(prop.title, prop.description)
            suspicious = detect_suspicious(prop.title, prop.description)

            prop.raw_data = prop.raw_data or {}
            prop.raw_data = {
                **(prop.raw_data if isinstance(prop.raw_data, dict) else {}),
                "is_direct_owner": is_direct,
                "suspicious_flags": suspicious,
            }

            if is_direct:
                direct += 1

        await session.commit()

    logger.info(f"Clasificación: {direct} avisos de dueño directo")
    return direct


async def auto_hide_bad_listings():
    """Oculta automáticamente avisos con 3+ feedbacks negativos en 1 hora."""
    logger.info("Verificando avisos gancho...")
    hidden = 0
    one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)

    async with async_session() as session:
        # Buscar propiedades con 3+ feedbacks negativos recientes
        stmt = (
            select(Feedback.property_id, func.count().label("bad_count"))
            .where(
                Feedback.is_good.is_(False),
                Feedback.created_at >= one_hour_ago,
            )
            .group_by(Feedback.property_id)
            .having(func.count() >= 3)
        )
        result = await session.execute(stmt)

        for row in result.all():
            property_id = row[0]
            update_stmt = (
                update(Property)
                .where(Property.id == property_id, Property.is_active.is_(True))
                .values(is_active=False, updated_at=datetime.now(timezone.utc))
            )
            res = await session.execute(update_stmt)
            if res.rowcount > 0:
                hidden += 1
                logger.warning(f"Aviso gancho ocultado: {property_id}")

        await session.commit()

    if hidden > 0:
        logger.info(f"Auto-ocultados: {hidden} avisos gancho")
    return hidden
