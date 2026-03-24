from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Base de datos
    database_url: str = "postgresql+asyncpg://inmoalert:inmoalert_pass@db:5432/inmoalert"

    # Redis
    redis_url: str = "redis://redis:6379/0"

    # Telegram
    telegram_bot_token: str = ""
    telegram_admin_chat_id: str = ""

    # UF
    uf_api_url: str = "https://mindicador.cl/api/uf"

    # Scraping
    scraping_interval_hours: int = 4
    scraping_delay_min: int = 3
    scraping_delay_max: int = 8

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

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
