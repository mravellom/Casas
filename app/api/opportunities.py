from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models.market_average import MarketAverage
from app.models.property import Property

router = APIRouter(prefix="/api/v1/opportunities", tags=["opportunities"])


@router.get("")
async def list_opportunities(
    commune: str | None = None,
    min_score: int = Query(70, ge=0, le=100),
    min_uf: float | None = Query(None, ge=0),
    max_uf: float | None = Query(None, ge=0),
    bedrooms: int | None = Query(None, ge=1, le=5),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    """Lista oportunidades detectadas, ordenadas por score descendente."""
    stmt = select(Property).where(
        Property.is_opportunity == True,  # noqa: E712
        Property.is_active == True,  # noqa: E712
        Property.opportunity_score >= min_score,
    )

    if commune:
        stmt = stmt.where(Property.commune == commune)
    if min_uf is not None:
        stmt = stmt.where(Property.price_uf >= min_uf)
    if max_uf is not None:
        stmt = stmt.where(Property.price_uf <= max_uf)
    if bedrooms is not None:
        stmt = stmt.where(Property.bedrooms == bedrooms)

    # Contar total
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await session.execute(count_stmt)).scalar()

    # Paginar y ordenar por score desc
    offset = (page - 1) * limit
    stmt = stmt.order_by(Property.opportunity_score.desc()).offset(offset).limit(limit)
    result = await session.execute(stmt)
    properties = result.scalars().all()

    # Cargar promedios para calcular % bajo mercado
    avg_stmt = select(MarketAverage)
    avg_result = await session.execute(avg_stmt)
    averages = {
        (ma.commune, ma.bedrooms): ma for ma in avg_result.scalars().all()
    }

    data = []
    for p in properties:
        market_avg = averages.get((p.commune, p.bedrooms))
        avg_price_m2 = float(market_avg.avg_price_m2_uf) if market_avg else None
        pct_below = None
        estimated_value = None

        if avg_price_m2 and p.price_m2_uf and p.m2_total:
            pct_below = round(
                ((float(p.price_m2_uf) - avg_price_m2) / avg_price_m2) * 100, 1
            )
            estimated_value = round(avg_price_m2 * float(p.m2_total), 1)

        data.append({
            "id": str(p.id),
            "source": p.source,
            "source_url": p.source_url,
            "title": p.title,
            "price_uf": float(p.price_uf) if p.price_uf else None,
            "price_m2_uf": float(p.price_m2_uf) if p.price_m2_uf else None,
            "m2_total": float(p.m2_total) if p.m2_total else None,
            "bedrooms": p.bedrooms,
            "commune": p.commune,
            "opportunity_score": p.opportunity_score,
            "has_urgency_keyword": p.has_urgency_keyword,
            "pct_below_market": pct_below,
            "avg_zone_price_m2": avg_price_m2,
            "estimated_market_value_uf": estimated_value,
            "potential_profit_uf": (
                round(estimated_value - float(p.price_uf), 1)
                if estimated_value and p.price_uf
                else None
            ),
            "first_seen_at": p.first_seen_at.isoformat() if p.first_seen_at else None,
        })

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "data": data,
    }


@router.get("/top")
async def top_opportunities(
    limit: int = Query(10, ge=1, le=50),
    session: AsyncSession = Depends(get_session),
):
    """Top oportunidades del día ordenadas por score."""
    stmt = (
        select(Property)
        .where(
            Property.is_opportunity == True,  # noqa: E712
            Property.is_active == True,  # noqa: E712
        )
        .order_by(Property.opportunity_score.desc())
        .limit(limit)
    )
    result = await session.execute(stmt)
    properties = result.scalars().all()

    # Cargar promedios
    avg_stmt = select(MarketAverage)
    avg_result = await session.execute(avg_stmt)
    averages = {
        (ma.commune, ma.bedrooms): ma for ma in avg_result.scalars().all()
    }

    data = []
    for p in properties:
        market_avg = averages.get((p.commune, p.bedrooms))
        avg_price_m2 = float(market_avg.avg_price_m2_uf) if market_avg else None
        pct_below = None

        if avg_price_m2 and p.price_m2_uf:
            pct_below = round(
                ((float(p.price_m2_uf) - avg_price_m2) / avg_price_m2) * 100, 1
            )

        data.append({
            "id": str(p.id),
            "source": p.source,
            "source_url": p.source_url,
            "title": p.title,
            "price_uf": float(p.price_uf) if p.price_uf else None,
            "m2_total": float(p.m2_total) if p.m2_total else None,
            "bedrooms": p.bedrooms,
            "commune": p.commune,
            "score": p.opportunity_score,
            "pct_below_market": pct_below,
        })

    return {"data": data}


@router.get("/market")
async def market_averages(
    commune: str | None = None,
    session: AsyncSession = Depends(get_session),
):
    """Promedios de mercado UF/m² por comuna."""
    stmt = select(MarketAverage)
    if commune:
        stmt = stmt.where(MarketAverage.commune == commune)
    stmt = stmt.order_by(MarketAverage.commune, MarketAverage.bedrooms)

    result = await session.execute(stmt)
    averages = result.scalars().all()

    return {
        "data": [
            {
                "commune": ma.commune,
                "bedrooms": ma.bedrooms,
                "avg_price_m2_uf": float(ma.avg_price_m2_uf),
                "median_price_m2_uf": (
                    float(ma.median_price_m2_uf)
                    if ma.median_price_m2_uf
                    else None
                ),
                "min_price_m2_uf": (
                    float(ma.min_price_m2_uf) if ma.min_price_m2_uf else None
                ),
                "max_price_m2_uf": (
                    float(ma.max_price_m2_uf) if ma.max_price_m2_uf else None
                ),
                "sample_count": ma.sample_count,
                "last_updated": ma.last_updated.isoformat() if ma.last_updated else None,
            }
            for ma in averages
        ]
    }
