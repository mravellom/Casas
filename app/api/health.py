import asyncio
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks

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
async def health_check():
    return {
        "status": "ok",
        "service": "InmoAlert Chile",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/scrape/trigger")
async def trigger_pipeline(background_tasks: BackgroundTasks):
    """Dispara el pipeline completo: scraping → dedup → pricing → scoring."""
    if _pipeline_status["running"]:
        return {"status": "already_running", "message": "Pipeline ya está en ejecución"}

    background_tasks.add_task(_run_pipeline_with_status)
    return {"status": "started", "message": "Pipeline completo iniciado en background"}


@router.get("/scrape/status")
async def pipeline_status():
    return _pipeline_status


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
