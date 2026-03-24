import logging
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models.feedback import Feedback
from app.models.property import Property
from app.workers.monitor import get_pipeline_runs, get_system_metrics
from app.workers.scrape_job import run_full_pipeline

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])

logger = logging.getLogger(__name__)

# Estado del último pipeline
_pipeline_status = {
    "running": False,
    "last_run": None,
    "last_error": None,
}


@router.get("/health")
async def health_check(session: AsyncSession = Depends(get_session)):
    """Health check con info de BD."""
    try:
        result = await session.execute(
            select(func.count()).select_from(Property)
        )
        property_count = result.scalar() or 0
        db_status = "connected"
    except Exception:
        property_count = 0
        db_status = "error"

    return {
        "status": "ok",
        "service": "InmoAlert Chile",
        "version": "0.1.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "database": db_status,
        "properties_in_db": property_count,
    }


@router.post("/scrape/trigger")
async def trigger_pipeline(background_tasks: BackgroundTasks):
    """Dispara el pipeline completo: scraping → dedup → pricing → scoring → alertas."""
    if _pipeline_status["running"]:
        return {"status": "already_running", "message": "Pipeline ya está en ejecución"}

    background_tasks.add_task(_run_pipeline_with_status)
    return {"status": "started", "message": "Pipeline completo iniciado en background"}


@router.get("/scrape/status")
async def pipeline_status():
    return _pipeline_status


@router.get("/metrics")
async def metrics():
    """Métricas del sistema: propiedades, oportunidades, usuarios, alertas."""
    return await get_system_metrics()


@router.get("/logs")
async def pipeline_logs(limit: int = Query(10, ge=1, le=50)):
    """Últimas ejecuciones del pipeline."""
    return {"runs": get_pipeline_runs(limit)}


@router.get("/feedback/stats")
async def feedback_stats(session: AsyncSession = Depends(get_session)):
    """Estadísticas de feedback: tasa de falsos positivos."""
    # Total feedback
    total_stmt = select(func.count()).select_from(Feedback)
    total = (await session.execute(total_stmt)).scalar() or 0

    if total == 0:
        return {
            "total_feedback": 0,
            "good": 0,
            "bad": 0,
            "false_positive_rate": None,
            "message": "Sin feedback todavía",
        }

    # Buenos
    good_stmt = (
        select(func.count())
        .select_from(Feedback)
        .where(Feedback.is_good == True)  # noqa: E712
    )
    good = (await session.execute(good_stmt)).scalar() or 0

    bad = total - good
    fp_rate = round((bad / total) * 100, 1)

    return {
        "total_feedback": total,
        "good": good,
        "bad": bad,
        "false_positive_rate": fp_rate,
        "target": "< 30%",
        "status": "OK" if fp_rate < 30 else "NEEDS_ADJUSTMENT",
    }


async def _run_pipeline_with_status():
    _pipeline_status["running"] = True
    _pipeline_status["last_error"] = None
    try:
        await run_full_pipeline()
        _pipeline_status["last_run"] = datetime.now(timezone.utc).isoformat()
    except Exception as e:
        logger.error(f"Error en pipeline: {e}")
        _pipeline_status["last_error"] = str(e)
    finally:
        _pipeline_status["running"] = False
