from fastapi import Depends, HTTPException, Security
from fastapi.security import APIKeyHeader

from app.config import settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_admin_key(api_key: str | None = Security(api_key_header)) -> str:
    """Valida API key para endpoints admin protegidos."""
    if not settings.admin_api_key:
        # En desarrollo sin API key configurada, permitir acceso
        return "dev-mode"

    if not api_key or api_key != settings.admin_api_key:
        raise HTTPException(status_code=401, detail="API key inválida o faltante")

    return api_key
