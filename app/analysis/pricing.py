import logging
from datetime import datetime, timezone

import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import async_session
from app.models.market_average import MarketAverage
from app.models.property import Property

logger = logging.getLogger(__name__)


async def update_market_averages():
    """Recalcula promedios de UF/m² por comuna y dormitorios.

    Usa todas las propiedades activas con precio y m² válidos
    para calcular estadísticas por zona.
    """
    logger.info("Recalculando promedios de mercado...")
    updated_count = 0

    async with async_session() as session:
        for commune in settings.target_communes:
            for bedrooms in range(settings.min_bedrooms, settings.max_bedrooms + 1):
                stats = await _calculate_zone_stats(session, commune, bedrooms)
                if stats:
                    await _upsert_market_average(session, commune, bedrooms, stats)
                    updated_count += 1
                    logger.info(
                        f"  {commune} {bedrooms}d: "
                        f"avg={stats['avg']:.2f} UF/m², "
                        f"median={stats['median']:.2f}, "
                        f"n={stats['count']}"
                    )

        await session.commit()

    logger.info(f"Promedios actualizados: {updated_count} zonas")
    return updated_count


async def _calculate_zone_stats(
    session: AsyncSession, commune: str, bedrooms: int
) -> dict | None:
    """Calcula estadísticas de UF/m² para una comuna y tipo de dormitorio."""
    stmt = (
        select(Property.price_m2_uf)
        .where(
            Property.commune == commune,
            Property.bedrooms == bedrooms,
            Property.is_active == True,  # noqa: E712
            Property.price_m2_uf.isnot(None),
            Property.price_m2_uf > 0,
        )
    )
    result = await session.execute(stmt)
    prices = [float(row[0]) for row in result.all()]

    if len(prices) < 3:
        logger.warning(
            f"  {commune} {bedrooms}d: solo {len(prices)} propiedades, "
            f"mínimo 3 para calcular promedio"
        )
        return None

    arr = np.array(prices)

    # Eliminar outliers usando IQR (rango intercuartílico)
    q1 = np.percentile(arr, 25)
    q3 = np.percentile(arr, 75)
    iqr = q3 - q1
    lower_bound = q1 - 1.5 * iqr
    upper_bound = q3 + 1.5 * iqr
    filtered = arr[(arr >= lower_bound) & (arr <= upper_bound)]

    if len(filtered) < 3:
        filtered = arr  # Si quedan muy pocos, usar todos

    return {
        "avg": float(np.mean(filtered)),
        "median": float(np.median(filtered)),
        "min": float(np.min(filtered)),
        "max": float(np.max(filtered)),
        "std": float(np.std(filtered)),
        "count": len(filtered),
    }


async def _upsert_market_average(
    session: AsyncSession, commune: str, bedrooms: int, stats: dict
):
    """Inserta o actualiza el promedio de mercado para una zona."""
    stmt = select(MarketAverage).where(
        MarketAverage.commune == commune,
        MarketAverage.bedrooms == bedrooms,
    )
    result = await session.execute(stmt)
    existing = result.scalar_one_or_none()

    now = datetime.now(timezone.utc)

    if existing:
        existing.avg_price_m2_uf = stats["avg"]
        existing.median_price_m2_uf = stats["median"]
        existing.min_price_m2_uf = stats["min"]
        existing.max_price_m2_uf = stats["max"]
        existing.std_deviation = stats["std"]
        existing.sample_count = stats["count"]
        existing.last_updated = now
    else:
        new_avg = MarketAverage(
            commune=commune,
            bedrooms=bedrooms,
            avg_price_m2_uf=stats["avg"],
            median_price_m2_uf=stats["median"],
            min_price_m2_uf=stats["min"],
            max_price_m2_uf=stats["max"],
            std_deviation=stats["std"],
            sample_count=stats["count"],
            last_updated=now,
        )
        session.add(new_avg)


async def get_zone_average(
    session: AsyncSession, commune: str, bedrooms: int
) -> float | None:
    """Obtiene el promedio UF/m² para una zona. Retorna None si no existe."""
    stmt = select(MarketAverage.avg_price_m2_uf).where(
        MarketAverage.commune == commune,
        MarketAverage.bedrooms == bedrooms,
    )
    result = await session.execute(stmt)
    row = result.scalar_one_or_none()
    return float(row) if row is not None else None
