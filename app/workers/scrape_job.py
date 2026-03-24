import logging
from datetime import datetime, timezone

from sqlalchemy import select

from sqlalchemy import select as sa_select

from app.analysis.filters import deduplicate_properties
from app.analysis.pricing import update_market_averages
from app.analysis.scoring import score_all_properties
from app.analysis.uf_converter import clp_to_uf, get_uf_value
from app.config import settings
from app.database import async_session
from app.models.property import Property
from app.notifications.telegram import send_opportunity_alerts
from app.scrapers.base import ScrapedProperty
from app.scrapers.portal_inmobiliario import PortalInmobiliarioScraper
from app.scrapers.yapo import YapoScraper

logger = logging.getLogger(__name__)


async def run_full_pipeline():
    """Ejecuta el pipeline completo: scraping → limpieza → pricing → scoring."""
    logger.info("========== PIPELINE COMPLETO INICIADO ==========")

    # Paso 1: Scraping
    await run_scraping()

    # Paso 2: Deduplicación
    try:
        dedup_count = await deduplicate_properties()
        logger.info(f"Paso 2 - Deduplicación: {dedup_count} duplicados eliminados")
    except Exception as e:
        logger.error(f"Error en deduplicación: {e}")

    # Paso 3: Recalcular promedios de mercado
    try:
        zones_updated = await update_market_averages()
        logger.info(f"Paso 3 - Promedios: {zones_updated} zonas actualizadas")
    except Exception as e:
        logger.error(f"Error en promedios de mercado: {e}")

    # Paso 4: Scoring de oportunidades
    try:
        scored, opportunities = await score_all_properties()
        logger.info(
            f"Paso 4 - Scoring: {scored} analizadas, {opportunities} oportunidades"
        )
    except Exception as e:
        logger.error(f"Error en scoring: {e}")

    # Paso 5: Enviar alertas por Telegram
    try:
        async with async_session() as session:
            stmt = (
                sa_select(Property)
                .where(
                    Property.is_opportunity == True,  # noqa: E712
                    Property.is_active == True,  # noqa: E712
                    Property.opportunity_score >= settings.opportunity_min_score,
                )
                .order_by(Property.opportunity_score.desc())
            )
            result = await session.execute(stmt)
            new_opportunities = list(result.scalars().all())

        if new_opportunities:
            sent = await send_opportunity_alerts(new_opportunities)
            logger.info(f"Paso 5 - Alertas: {sent} notificaciones enviadas")
        else:
            logger.info("Paso 5 - Alertas: sin oportunidades para notificar")
    except Exception as e:
        logger.error(f"Error en alertas: {e}")

    logger.info("========== PIPELINE COMPLETO FINALIZADO ==========")


async def run_scraping():
    """Ejecuta el scraping de todos los portales y guarda en BD."""
    logger.info("=== Paso 1: Scraping ===")

    # Obtener valor UF del día
    try:
        uf_value = await get_uf_value()
        logger.info(f"Valor UF del día: ${uf_value:,.2f} CLP")
    except ValueError:
        logger.error("No se pudo obtener el valor UF. Abortando scraping.")
        return

    all_properties: list[ScrapedProperty] = []

    # Scrape Portal Inmobiliario
    try:
        pi_scraper = PortalInmobiliarioScraper()
        pi_props = await pi_scraper.scrape()
        all_properties.extend(pi_props)
        logger.info(f"Portal Inmobiliario: {len(pi_props)} propiedades")
    except Exception as e:
        logger.error(f"Error en scraping Portal Inmobiliario: {e}")

    # Scrape Yapo
    try:
        yapo_scraper = YapoScraper()
        yapo_props = await yapo_scraper.scrape()
        all_properties.extend(yapo_props)
        logger.info(f"Yapo: {len(yapo_props)} propiedades")
    except Exception as e:
        logger.error(f"Error en scraping Yapo: {e}")

    if not all_properties:
        logger.warning("No se encontraron propiedades en ningún portal")
        return

    # Filtrar por rango de precio y convertir CLP a UF
    filtered = _filter_and_convert(all_properties, uf_value)
    logger.info(f"Propiedades después de filtro: {len(filtered)}")

    # Guardar en BD
    saved, updated = await _save_properties(filtered)
    logger.info(f"Scraping completado: {saved} nuevas, {updated} actualizadas")


def _filter_and_convert(
    properties: list[ScrapedProperty], uf_value: float
) -> list[ScrapedProperty]:
    """Filtra por rango de precio y convierte CLP a UF."""
    filtered = []

    for prop in properties:
        # Convertir CLP a UF si no tiene precio en UF
        if prop.price_uf is None and prop.price_clp is not None:
            prop.price_uf = clp_to_uf(prop.price_clp, uf_value)

        # Descartar sin precio
        if prop.price_uf is None:
            continue

        # Filtrar por rango
        if not (settings.min_price_uf <= prop.price_uf <= settings.max_price_uf):
            continue

        # Descartar sin comuna válida
        if prop.commune not in settings.target_communes:
            continue

        filtered.append(prop)

    return filtered


async def _save_properties(
    properties: list[ScrapedProperty],
) -> tuple[int, int]:
    """Guarda propiedades en BD usando upsert (insert on conflict update)."""
    saved = 0
    updated = 0
    now = datetime.now(timezone.utc)

    async with async_session() as session:
        for prop in properties:
            # Calcular precio/m²
            price_m2 = None
            if prop.price_uf and prop.m2_total and prop.m2_total > 0:
                price_m2 = round(prop.price_uf / prop.m2_total, 2)

            # Verificar si ya existe
            stmt = select(Property).where(
                Property.source == prop.source,
                Property.source_id == prop.source_id,
            )
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing:
                # Actualizar last_seen_at y datos que pudieron cambiar
                existing.last_seen_at = now
                existing.price_uf = prop.price_uf
                existing.price_clp = prop.price_clp
                existing.price_m2_uf = price_m2
                existing.is_active = True
                existing.updated_at = now
                updated += 1
            else:
                # Insertar nueva propiedad
                new_prop = Property(
                    source=prop.source,
                    source_id=prop.source_id,
                    source_url=prop.source_url,
                    title=prop.title,
                    description=prop.description,
                    price_uf=prop.price_uf,
                    price_clp=prop.price_clp,
                    price_m2_uf=price_m2,
                    m2_total=prop.m2_total,
                    m2_util=prop.m2_util,
                    bedrooms=prop.bedrooms,
                    bathrooms=prop.bathrooms,
                    commune=prop.commune,
                    address=prop.address,
                    latitude=prop.latitude,
                    longitude=prop.longitude,
                    floor=prop.floor,
                    has_parking=prop.has_parking,
                    has_bodega=prop.has_bodega,
                    building_year=prop.building_year,
                    images=prop.images if prop.images else None,
                    raw_data=prop.raw_data if prop.raw_data else None,
                    first_seen_at=now,
                    last_seen_at=now,
                    created_at=now,
                    updated_at=now,
                )
                session.add(new_prop)
                saved += 1

        await session.commit()

    return saved, updated
