import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.config import settings
from app.workers.scrape_job import run_full_pipeline

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


def start_scheduler():
    """Inicia el scheduler con los jobs programados."""
    scheduler.add_job(
        run_full_pipeline,
        trigger=IntervalTrigger(hours=settings.scraping_interval_hours),
        id="full_pipeline",
        name="Pipeline completo (scraping + análisis)",
        replace_existing=True,
        max_instances=1,
    )

    scheduler.start()
    logger.info(
        f"Scheduler iniciado: pipeline cada {settings.scraping_interval_hours} horas"
    )


def stop_scheduler():
    """Detiene el scheduler."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler detenido")
