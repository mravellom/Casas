from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models.property import Property

router = APIRouter(prefix="/api/v1/properties", tags=["properties"])


@router.get("")
async def list_properties(
    commune: str | None = None,
    min_uf: float | None = Query(None, ge=0),
    max_uf: float | None = Query(None, ge=0),
    bedrooms: int | None = Query(None, ge=1, le=5),
    only_opportunities: bool = False,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    stmt = select(Property).where(Property.is_active == True)  # noqa: E712

    if commune:
        stmt = stmt.where(Property.commune == commune)
    if min_uf is not None:
        stmt = stmt.where(Property.price_uf >= min_uf)
    if max_uf is not None:
        stmt = stmt.where(Property.price_uf <= max_uf)
    if bedrooms is not None:
        stmt = stmt.where(Property.bedrooms == bedrooms)
    if only_opportunities:
        stmt = stmt.where(Property.is_opportunity == True)  # noqa: E712

    # Contar total
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await session.execute(count_stmt)).scalar()

    # Paginar
    offset = (page - 1) * limit
    stmt = stmt.order_by(Property.created_at.desc()).offset(offset).limit(limit)
    result = await session.execute(stmt)
    properties = result.scalars().all()

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "data": [
            {
                "id": str(p.id),
                "source": p.source,
                "source_url": p.source_url,
                "title": p.title,
                "price_uf": float(p.price_uf) if p.price_uf else None,
                "price_m2_uf": float(p.price_m2_uf) if p.price_m2_uf else None,
                "m2_total": float(p.m2_total) if p.m2_total else None,
                "bedrooms": p.bedrooms,
                "bathrooms": p.bathrooms,
                "commune": p.commune,
                "address": p.address,
                "is_opportunity": p.is_opportunity,
                "opportunity_score": p.opportunity_score,
                "first_seen_at": p.first_seen_at.isoformat() if p.first_seen_at else None,
            }
            for p in properties
        ],
    }


@router.get("/{property_id}")
async def get_property(
    property_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    stmt = select(Property).where(Property.id == property_id)
    result = await session.execute(stmt)
    prop = result.scalar_one_or_none()

    if not prop:
        return {"error": "Propiedad no encontrada"}, 404

    return {
        "id": str(prop.id),
        "source": prop.source,
        "source_id": prop.source_id,
        "source_url": prop.source_url,
        "title": prop.title,
        "description": prop.description,
        "price_uf": float(prop.price_uf) if prop.price_uf else None,
        "price_clp": prop.price_clp,
        "price_m2_uf": float(prop.price_m2_uf) if prop.price_m2_uf else None,
        "m2_total": float(prop.m2_total) if prop.m2_total else None,
        "m2_util": float(prop.m2_util) if prop.m2_util else None,
        "bedrooms": prop.bedrooms,
        "bathrooms": prop.bathrooms,
        "commune": prop.commune,
        "address": prop.address,
        "latitude": float(prop.latitude) if prop.latitude else None,
        "longitude": float(prop.longitude) if prop.longitude else None,
        "floor": prop.floor,
        "has_parking": prop.has_parking,
        "has_bodega": prop.has_bodega,
        "is_opportunity": prop.is_opportunity,
        "opportunity_score": prop.opportunity_score,
        "has_urgency_keyword": prop.has_urgency_keyword,
        "is_active": prop.is_active,
        "first_seen_at": prop.first_seen_at.isoformat() if prop.first_seen_at else None,
        "last_seen_at": prop.last_seen_at.isoformat() if prop.last_seen_at else None,
        "images": prop.images,
    }
