import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.api.opportunities import router as opportunities_router
from app.api.properties import router as properties_router
from app.database import init_db
from app.notifications.telegram import build_telegram_app
from app.workers.scheduler import start_scheduler, stop_scheduler

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)

# Referencia global al bot
_telegram_app = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _telegram_app

    await init_db()
    start_scheduler()

    # Iniciar bot de Telegram en background
    try:
        _telegram_app = build_telegram_app()
        if _telegram_app:
            await _telegram_app.initialize()
            await _telegram_app.start()
            await _telegram_app.updater.start_polling(drop_pending_updates=True)
            logger.info("Bot de Telegram iniciado")
    except Exception as e:
        logger.warning(f"Bot de Telegram no iniciado: {e}")
        _telegram_app = None

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
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(properties_router)
app.include_router(opportunities_router)
