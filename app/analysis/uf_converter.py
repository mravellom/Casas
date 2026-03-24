import logging
from datetime import date

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# Cache en memoria del valor UF del día
_uf_cache: dict[str, float] = {}


async def get_uf_value(target_date: date | None = None) -> float:
    """Obtiene el valor de la UF para una fecha dada (default: hoy).

    Consulta la API de mindicador.cl y cachea el resultado por día.
    """
    target_date = target_date or date.today()
    cache_key = target_date.isoformat()

    if cache_key in _uf_cache:
        return _uf_cache[cache_key]

    try:
        url = f"{settings.uf_api_url}/{target_date.strftime('%d-%m-%Y')}"
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()

        if data.get("serie") and len(data["serie"]) > 0:
            valor = float(data["serie"][0]["valor"])
            _uf_cache[cache_key] = valor
            logger.info(f"UF {target_date}: ${valor:,.2f} CLP")
            return valor

        # Si no hay datos para esa fecha, intentar sin fecha (último valor)
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(settings.uf_api_url)
            response.raise_for_status()
            data = response.json()

        if data.get("serie") and len(data["serie"]) > 0:
            valor = float(data["serie"][0]["valor"])
            _uf_cache[cache_key] = valor
            logger.info(f"UF (último disponible): ${valor:,.2f} CLP")
            return valor

    except Exception as e:
        logger.error(f"Error obteniendo valor UF: {e}")

        # Fallback: usar último valor cacheado
        if _uf_cache:
            last_value = list(_uf_cache.values())[-1]
            logger.warning(f"Usando último valor UF cacheado: ${last_value:,.2f}")
            return last_value

    raise ValueError("No se pudo obtener el valor de la UF")


def clp_to_uf(clp: int | float, uf_value: float) -> float:
    """Convierte pesos chilenos a UF."""
    if uf_value <= 0:
        raise ValueError("Valor UF inválido")
    return round(clp / uf_value, 2)


def uf_to_clp(uf: float, uf_value: float) -> int:
    """Convierte UF a pesos chilenos."""
    if uf_value <= 0:
        raise ValueError("Valor UF inválido")
    return round(uf * uf_value)


def clear_cache():
    """Limpia el cache de UF (para tests)."""
    _uf_cache.clear()
