"""Calculador de rentabilidad inmobiliaria.

Calcula Cap Rate, Payback Period y ROI para cada propiedad
basándose en arriendos promedio de la zona.
"""
import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import async_session
from app.models.property import Property
from app.models.rent_average import RentAverage

logger = logging.getLogger(__name__)

# Gastos comunes estimados por m² en UF/mes
DEFAULT_EXPENSES_PER_M2 = 0.08


@dataclass
class RentabilityResult:
    estimated_rent_uf: float  # Arriendo estimado mensual UF
    cap_rate: float           # Rentabilidad bruta anual %
    cap_rate_net: float       # Rentabilidad neta anual %
    payback_years: float      # Años para recuperar inversión
    roi_annual: float         # ROI anual neto %
    monthly_expenses_uf: float  # Gastos comunes estimados
    monthly_cashflow_uf: float  # Flujo de caja mensual neto
    is_high_rentability: bool   # Cap Rate > 6%


def calculate_rentability(
    price_uf: float,
    monthly_rent_uf: float,
    m2_total: float | None = None,
    expenses_per_m2: float = DEFAULT_EXPENSES_PER_M2,
) -> RentabilityResult:
    """Calcula métricas de rentabilidad para una propiedad."""
    annual_rent = monthly_rent_uf * 12

    # Gastos comunes mensuales
    monthly_expenses = (m2_total or 40) * expenses_per_m2

    # Cap Rate bruto
    cap_rate = (annual_rent / price_uf) * 100

    # Cap Rate neto (descontando gastos)
    annual_expenses = monthly_expenses * 12
    cap_rate_net = ((annual_rent - annual_expenses) / price_uf) * 100

    # Payback (bruto)
    payback_years = price_uf / annual_rent if annual_rent > 0 else 999

    # ROI neto
    roi_annual = cap_rate_net

    # Flujo de caja mensual
    monthly_cashflow = monthly_rent_uf - monthly_expenses

    return RentabilityResult(
        estimated_rent_uf=round(monthly_rent_uf, 2),
        cap_rate=round(cap_rate, 2),
        cap_rate_net=round(cap_rate_net, 2),
        payback_years=round(payback_years, 1),
        roi_annual=round(roi_annual, 2),
        monthly_expenses_uf=round(monthly_expenses, 2),
        monthly_cashflow_uf=round(monthly_cashflow, 2),
        is_high_rentability=cap_rate > 6.0,
    )


async def get_estimated_rent(
    session: AsyncSession, commune: str, bedrooms: int
) -> float | None:
    """Obtiene el arriendo promedio para una zona."""
    stmt = select(RentAverage.avg_rent_uf).where(
        RentAverage.commune == commune,
        RentAverage.bedrooms == bedrooms,
    )
    result = await session.execute(stmt)
    value = result.scalar_one_or_none()
    return float(value) if value is not None else None


async def calculate_all_rentabilities():
    """Calcula rentabilidad para todas las oportunidades activas."""
    logger.info("Calculando rentabilidades...")
    calculated = 0

    async with async_session() as session:
        # Cargar promedios de arriendo
        stmt = select(RentAverage)
        result = await session.execute(stmt)
        rents = {
            (r.commune, r.bedrooms): float(r.avg_rent_uf)
            for r in result.scalars().all()
        }

        if not rents:
            logger.warning("Sin datos de arriendo. Ejecuta el scraper de arriendos primero.")
            return 0

        # Propiedades activas con precio
        stmt = select(Property).where(
            Property.is_active.is_(True),
            Property.price_uf.isnot(None),
            Property.price_uf > 0,
        )
        result = await session.execute(stmt)

        for prop in result.scalars().all():
            key = (prop.commune, prop.bedrooms or 1)
            rent = rents.get(key)
            if not rent or not prop.price_uf:
                continue

            r = calculate_rentability(
                float(prop.price_uf), rent, float(prop.m2_total) if prop.m2_total else None
            )

            # Guardar en raw_data para acceso rápido
            prop.raw_data = prop.raw_data or {}
            prop.raw_data = {
                **(prop.raw_data if isinstance(prop.raw_data, dict) else {}),
                "rentability": {
                    "estimated_rent_uf": r.estimated_rent_uf,
                    "cap_rate": r.cap_rate,
                    "cap_rate_net": r.cap_rate_net,
                    "payback_years": r.payback_years,
                    "roi_annual": r.roi_annual,
                    "monthly_expenses_uf": r.monthly_expenses_uf,
                    "monthly_cashflow_uf": r.monthly_cashflow_uf,
                    "is_high_rentability": r.is_high_rentability,
                },
            }
            prop.updated_at = datetime.now(timezone.utc)
            calculated += 1

        await session.commit()

    logger.info(f"Rentabilidad calculada para {calculated} propiedades")
    return calculated
