import logging

from pydantic import model_validator
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    # Entorno
    environment: str = "development"

    # Base de datos (sin default inseguro)
    database_url: str = "postgresql+asyncpg://inmoalert:inmoalert_pass@localhost:5435/inmoalert"

    # Redis
    redis_url: str = "redis://localhost:6382/0"

    # Telegram
    telegram_bot_token: str = ""
    telegram_admin_chat_id: str = ""

    # UF
    uf_api_url: str = "https://mindicador.cl/api/uf"

    # Scraping
    scraping_interval_hours: int = 4
    scraping_delay_min: int = 3
    scraping_delay_max: int = 8
    scraping_max_requests_per_session: int = 100

    # Oportunidades
    opportunity_min_score: int = 70
    price_deviation_threshold: float = -15.0
    max_alerts_per_day: int = 5

    # Comunas objetivo
    target_communes: list[str] = [
        "Santiago Centro",
        "San Miguel",
        "Estación Central",
        "Ñuñoa",
    ]

    # Rango de precio UF
    min_price_uf: float = 1500.0
    max_price_uf: float = 4000.0

    # Dormitorios
    min_bedrooms: int = 1
    max_bedrooms: int = 2

    # Security
    admin_api_key: str = ""
    cors_origins: list[str] = ["http://localhost:3000"]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @model_validator(mode="after")
    def validate_production(self):
        if self.environment == "production":
            if not self.telegram_bot_token:
                raise ValueError("TELEGRAM_BOT_TOKEN requerido en producción")
            if not self.admin_api_key:
                raise ValueError("ADMIN_API_KEY requerido en producción")
            if "inmoalert_pass" in self.database_url:
                raise ValueError("Credenciales por defecto detectadas en producción")
        return self


settings = Settings()
