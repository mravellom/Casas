import logging
from collections import OrderedDict
from datetime import date

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.config import settings

logger = logging.getLogger(__name__)

# Cache bounded: máximo 30 fechas (último mes)
_MAX_CACHE_SIZE = 30
_uf_cache: OrderedDict[str, float] = OrderedDict()


def _cache_set(key: str, value: float) -> None:
    """Guarda en cache con evicción LRU."""
    _uf_cache[key] = value
    if len(_uf_cache) > _MAX_CACHE_SIZE:
        _uf_cache.popitem(last=False)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
    reraise=True,
)
async def _fetch_uf_from_api(url: str) -> dict:
    """Fetch con retry y circuit breaker."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.json()


async def get_uf_value(target_date: date | None = None) -> float:
    """Obtiene el valor de la UF para una fecha dada (default: hoy).

    Consulta la API de mindicador.cl con retry y cache bounded.
    """
    target_date = target_date or date.today()
    cache_key = target_date.isoformat()

    if cache_key in _uf_cache:
        return _uf_cache[cache_key]

    try:
        url = f"{settings.uf_api_url}/{target_date.strftime('%d-%m-%Y')}"
        data = await _fetch_uf_from_api(url)

        if data.get("serie") and len(data["serie"]) > 0:
            valor = float(data["serie"][0]["valor"])
            _cache_set(cache_key, valor)
            logger.info(f"UF {target_date}: ${valor:,.2f} CLP")
            return valor

        # Fallback: último valor disponible
        data = await _fetch_uf_from_api(settings.uf_api_url)
        if data.get("serie") and len(data["serie"]) > 0:
            valor = float(data["serie"][0]["valor"])
            _cache_set(cache_key, valor)
            logger.info(f"UF (último disponible): ${valor:,.2f} CLP")
            return valor

    except Exception as e:
        logger.error(f"Error obteniendo valor UF después de reintentos: {e}")

        # Fallback: usar último valor cacheado
        if _uf_cache:
            last_value = next(reversed(_uf_cache.values()))
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
