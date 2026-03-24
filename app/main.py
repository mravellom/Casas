import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.api.opportunities import router as opportunities_router
from app.api.properties import router as properties_router
from app.config import settings
from app.database import init_db
from app.notifications.telegram import build_telegram_app
from app.workers.scheduler import start_scheduler, stop_scheduler

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)

# Referencia global al bot y su estado
_telegram_app = None
_telegram_healthy = False


def get_telegram_status() -> str:
    """Retorna el estado del bot de Telegram."""
    if _telegram_healthy:
        return "connected"
    if settings.telegram_bot_token and settings.telegram_bot_token != "your_bot_token_here":
        return "failed"
    return "not_configured"


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _telegram_app

    await init_db()
    start_scheduler()

    # Iniciar bot de Telegram en background
    global _telegram_healthy
    try:
        _telegram_app = build_telegram_app()
        if _telegram_app:
            await _telegram_app.initialize()
            await _telegram_app.start()
            await _telegram_app.updater.start_polling(drop_pending_updates=True)
            _telegram_healthy = True
            logger.info("Bot de Telegram iniciado")
    except Exception as e:
        logger.warning(f"Bot de Telegram no iniciado: {e}")
        _telegram_app = None
        _telegram_healthy = False

    yield

    # Detener bot de Telegram
    if _telegram_app:
        await _telegram_app.updater.stop()
        await _telegram_app.stop()
        await _telegram_app.shutdown()
        logger.info("Bot de Telegram detenido")

    stop_scheduler()


app = FastAPI(
    title="InmoAlert Chile",
    description="Plataforma de inteligencia de oportunidades inmobiliarias - Santiago, Chile",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization", "X-API-Key"],
)

app.include_router(health_router)
app.include_router(properties_router)
app.include_router(opportunities_router)
