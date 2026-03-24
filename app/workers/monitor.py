import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from telegram import Bot

from app.config import settings
from app.database import async_session
from app.models.notification_log import NotificationLog
from app.models.property import Property
from app.models.user import User

logger = logging.getLogger(__name__)

# Historial de ejecuciones del pipeline
pipeline_runs: list[dict] = []
MAX_RUNS_HISTORY = 50


def record_pipeline_run(
    status: str,
    properties_found: int = 0,
    opportunities_found: int = 0,
    alerts_sent: int = 0,
    errors: list[str] | None = None,
    duration_seconds: float = 0,
):
    """Registra una ejecución del pipeline en el historial."""
    run = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "properties_found": properties_found,
        "opportunities_found": opportunities_found,
        "alerts_sent": alerts_sent,
        "errors": errors or [],
        "duration_seconds": round(duration_seconds, 2),
    }
    pipeline_runs.append(run)
    if len(pipeline_runs) > MAX_RUNS_HISTORY:
        pipeline_runs.pop(0)


def get_pipeline_runs(limit: int = 10) -> list[dict]:
    """Retorna las últimas N ejecuciones del pipeline."""
    return list(reversed(pipeline_runs[-limit:]))


async def notify_admin(message: str):
    """Envía un mensaje al admin vía Telegram."""
    if not settings.telegram_bot_token or not settings.telegram_admin_chat_id:
        logger.warning("Admin Telegram no configurado. Mensaje: %s", message)
        return

    try:
        bot = Bot(token=settings.telegram_bot_token)
        await bot.send_message(
            chat_id=settings.telegram_admin_chat_id,
            text=f"[InmoAlert Admin]\n{message}",
        )
    except Exception as e:
        logger.error(f"Error notificando al admin: {e}")


async def notify_scraping_error(source: str, error: str):
    """Alerta al admin cuando un scraper falla."""
    await notify_admin(
        f"ERROR en scraping de {source}:\n{error}\n\n"
        "El pipeline continuó con las otras fuentes."
    )


async def notify_no_properties():
    """Alerta al admin cuando no se encontraron propiedades."""
    await notify_admin(
        "ALERTA: El último scraping no encontró propiedades en ningún portal.\n"
        "Posibles causas:\n"
        "- Los portales cambiaron su estructura HTML\n"
        "- IPs bloqueadas\n"
        "- Problemas de conectividad"
    )


async def notify_pipeline_success(
    properties: int, opportunities: int, alerts: int, duration: float
):
    """Notifica al admin un resumen del pipeline exitoso (solo si hay oportunidades)."""
    if opportunities > 0:
        await notify_admin(
            f"Pipeline completado en {duration:.0f}s\n"
            f"Propiedades: {properties}\n"
            f"Oportunidades: {opportunities}\n"
            f"Alertas enviadas: {alerts}"
        )


async def get_system_metrics() -> dict:
    """Recopila métricas del sistema para el endpoint /admin/metrics."""
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = now - timedelta(days=7)

    async with async_session() as session:
        # Total propiedades activas
        total_active = (
            await session.execute(
                select(func.count())
                .select_from(Property)
                .where(Property.is_active == True)  # noqa: E712
            )
        ).scalar() or 0

        # Propiedades nuevas hoy
        new_today = (
            await session.execute(
                select(func.count())
                .select_from(Property)
                .where(Property.created_at >= today_start)
            )
        ).scalar() or 0

        # Oportunidades activas
        opportunities_active = (
            await session.execute(
                select(func.count())
                .select_from(Property)
                .where(
                    Property.is_opportunity == True,  # noqa: E712
                    Property.is_active == True,  # noqa: E712
                )
            )
        ).scalar() or 0

        # Oportunidades detectadas hoy
        opportunities_today = (
            await session.execute(
                select(func.count())
                .select_from(Property)
                .where(
                    Property.is_opportunity == True,  # noqa: E712
                    Property.created_at >= today_start,
                )
            )
        ).scalar() or 0

        # Usuarios activos
        users_active = (
            await session.execute(
                select(func.count())
                .select_from(User)
                .where(User.is_active == True)  # noqa: E712
            )
        ).scalar() or 0

        # Total usuarios
        users_total = (
            await session.execute(
                select(func.count()).select_from(User)
            )
        ).scalar() or 0

        # Alertas enviadas hoy
        alerts_today = (
            await session.execute(
                select(func.count())
                .select_from(NotificationLog)
                .where(NotificationLog.sent_at >= today_start)
            )
        ).scalar() or 0

        # Alertas última semana
        alerts_week = (
            await session.execute(
                select(func.count())
                .select_from(NotificationLog)
                .where(NotificationLog.sent_at >= week_ago)
            )
        ).scalar() or 0

        # Propiedades por fuente
        by_source = {}
        source_stmt = (
            select(Property.source, func.count())
            .where(Property.is_active == True)  # noqa: E712
            .group_by(Property.source)
        )
        source_result = await session.execute(source_stmt)
        for source, count in source_result.all():
            by_source[source] = count

        # Propiedades por comuna
        by_commune = {}
        commune_stmt = (
            select(Property.commune, func.count())
            .where(Property.is_active == True)  # noqa: E712
            .group_by(Property.commune)
        )
        commune_result = await session.execute(commune_stmt)
        for commune, count in commune_result.all():
            by_commune[commune] = count

    return {
        "timestamp": now.isoformat(),
        "properties": {
            "total_active": total_active,
            "new_today": new_today,
            "by_source": by_source,
            "by_commune": by_commune,
        },
        "opportunities": {
            "active": opportunities_active,
            "detected_today": opportunities_today,
        },
        "users": {
            "total": users_total,
            "active": users_active,
        },
        "alerts": {
            "sent_today": alerts_today,
            "sent_this_week": alerts_week,
        },
        "pipeline": {
            "last_runs": get_pipeline_runs(5),
        },
    }
