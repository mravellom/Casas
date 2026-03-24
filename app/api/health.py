import asyncio
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks

from app.workers.scrape_job import run_scraping

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])

logger = logging.getLogger(__name__)

# Estado del último scraping
_scrape_status = {
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
async def trigger_scrape(background_tasks: BackgroundTasks):
    if _scrape_status["running"]:
        return {"status": "already_running", "message": "Scraping ya está en ejecución"}

    background_tasks.add_task(_run_scrape_with_status)
    return {"status": "started", "message": "Scraping iniciado en background"}


@router.get("/scrape/status")
async def scrape_status():
    return _scrape_status


async def _run_scrape_with_status():
    _scrape_status["running"] = True
    _scrape_status["last_error"] = None
    try:
        await run_scraping()
        _scrape_status["last_run"] = datetime.now(timezone.utc).isoformat()
    except Exception as e:
        logger.error(f"Error en scraping: {e}")
        _scrape_status["last_error"] = str(e)
    finally:
        _scrape_status["running"] = False
