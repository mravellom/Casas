from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models.market_average import MarketAverage
from app.models.property import Property
from app.reports.pdf_generator import generate_property_pdf

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])


@router.get("/property/{property_id}/pdf")
async def download_property_pdf(
    property_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    """Genera y descarga el dossier de inversión en PDF."""
    stmt = select(Property).where(Property.id == property_id)
    result = await session.execute(stmt)
    prop = result.scalar_one_or_none()

    if not prop:
        raise HTTPException(status_code=404, detail="Propiedad no encontrada")

    # Obtener promedio de mercado
    avg_stmt = select(MarketAverage).where(
        MarketAverage.commune == prop.commune,
        MarketAverage.bedrooms == (prop.bedrooms or 1),
    )
    avg_result = await session.execute(avg_stmt)
    market_avg = avg_result.scalar_one_or_none()
    avg_m2 = float(market_avg.avg_price_m2_uf) if market_avg else None

    # Armar dict con toda la data
    raw = prop.raw_data if isinstance(prop.raw_data, dict) else {}

    prop_data = {
        "title": prop.title,
        "commune": prop.commune,
        "address": prop.address,
        "price_uf": float(prop.price_uf) if prop.price_uf else 0,
        "price_m2_uf": float(prop.price_m2_uf) if prop.price_m2_uf else 0,
        "m2_total": float(prop.m2_total) if prop.m2_total else 0,
        "bedrooms": prop.bedrooms,
        "bathrooms": prop.bathrooms,
        "opportunity_score": prop.opportunity_score,
        "source_url": prop.source_url,
        "has_parking": prop.has_parking,
        "has_bodega": prop.has_bodega,
        "rentability": raw.get("rentability"),
        "neighborhood": raw.get("neighborhood"),
    }

    pdf_bytes = generate_property_pdf(prop_data, avg_m2)

    filename = f"inmoalert_{prop.commune.replace(' ', '_')}_{prop.opportunity_score or 0}pts.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
