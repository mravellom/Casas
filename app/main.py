import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.health import router as health_router
from app.api.properties import router as properties_router
from app.database import init_db

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="InmoAlert Chile",
    description="Plataforma de inteligencia de oportunidades inmobiliarias - Santiago, Chile",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(health_router)
app.include_router(properties_router)
