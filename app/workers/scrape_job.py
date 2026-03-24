import logging
import time
from datetime import datetime, timezone

from sqlalchemy import select

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
from app.workers.monitor import (
    notify_admin,
    notify_no_properties,
    notify_pipeline_success,
    notify_scraping_error,
    record_pipeline_run,
)

logger = logging.getLogger(__name__)


async def run_full_pipeline():
    """Ejecuta el pipeline completo: scraping → limpieza → pricing → scoring → alertas."""
    logger.info("========== PIPELINE COMPLETO INICIADO ==========")
    start_time = time.time()
    errors: list[str] = []
    properties_count = 0
    opportunities_count = 0
    alerts_count = 0

    # Paso 1: Scraping
    properties_count = await run_scraping()

    if properties_count == 0:
        await notify_no_properties()

    # Paso 2: Deduplicación
    try:
        dedup_count = await deduplicate_properties()
        logger.info(f"Paso 2 - Deduplicación: {dedup_count} duplicados eliminados")
    except Exception as e:
        logger.error(f"Error en deduplicación: {e}")
        errors.append(f"Dedup: {e}")

    # Paso 3: Recalcular promedios de mercado
    try:
        zones_updated = await update_market_averages()
        logger.info(f"Paso 3 - Promedios: {zones_updated} zonas actualizadas")
    except Exception as e:
        logger.error(f"Error en promedios de mercado: {e}")
        errors.append(f"Pricing: {e}")

    # Paso 4: Scoring de oportunidades
    try:
        scored, opportunities_count = await score_all_properties()
        logger.info(
            f"Paso 4 - Scoring: {scored} analizadas, {opportunities_count} oportunidades"
        )
    except Exception as e:
        logger.error(f"Error en scoring: {e}")
        errors.append(f"Scoring: {e}")

    # Paso 5: Enviar alertas por Telegram
    try:
        async with async_session() as session:
            stmt = (
                select(Property)
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
            alerts_count = await send_opportunity_alerts(new_opportunities)
            logger.info(f"Paso 5 - Alertas: {alerts_count} notificaciones enviadas")
        else:
            logger.info("Paso 5 - Alertas: sin oportunidades para notificar")
    except Exception as e:
        logger.error(f"Error en alertas: {e}")
        errors.append(f"Alertas: {e}")

    # Paso 6: Limpiar propiedades inactivas
    try:
        from app.workers.cleanup import mark_stale_properties
        stale = await mark_stale_properties()
        logger.info(f"Paso 6 - Limpieza: {stale} propiedades marcadas como inactivas")
    except Exception as e:
        logger.error(f"Error en limpieza: {e}")
        errors.append(f"Limpieza: {e}")

    duration = time.time() - start_time
    status = "success" if not errors else "partial_error"

    # Registrar ejecución
    record_pipeline_run(
        status=status,
        properties_found=properties_count,
        opportunities_found=opportunities_count,
        alerts_sent=alerts_count,
        errors=errors,
        duration_seconds=duration,
    )

    # Notificar al admin
    if errors:
        await notify_admin(
            f"Pipeline completado con errores ({duration:.0f}s):\n"
            + "\n".join(f"- {e}" for e in errors)
        )
    else:
        await notify_pipeline_success(
            properties_count, opportunities_count, alerts_count, duration
        )

    logger.info(f"========== PIPELINE FINALIZADO ({duration:.1f}s) ==========")


async def run_scraping() -> int:
    """Ejecuta el scraping de todos los portales y guarda en BD.

    Retorna la cantidad de propiedades guardadas.
    """
    logger.info("=== Paso 1: Scraping ===")

    # Obtener valor UF del día
    try:
        uf_value = await get_uf_value()
        logger.info(f"Valor UF del día: ${uf_value:,.2f} CLP")
    except ValueError:
        logger.error("No se pudo obtener el valor UF. Abortando scraping.")
        await notify_admin("ERROR CRÍTICO: No se pudo obtener el valor UF")
        return 0

    all_properties: list[ScrapedProperty] = []

    # Scrape Portal Inmobiliario
    try:
        pi_scraper = PortalInmobiliarioScraper()
        pi_props = await pi_scraper.scrape()
        all_properties.extend(pi_props)
        logger.info(f"Portal Inmobiliario: {len(pi_props)} propiedades")
    except Exception as e:
        logger.error(f"Error en scraping Portal Inmobiliario: {e}")
        await notify_scraping_error("Portal Inmobiliario", str(e))

    # Scrape Mercado Libre Inmuebles (reemplaza a Yapo.cl que fue cerrado)
    try:
        from app.scrapers.yapo import MercadoLibreInmueblesScraper
        ml_scraper = MercadoLibreInmueblesScraper()
        ml_props = await ml_scraper.scrape()
        all_properties.extend(ml_props)
        logger.info(f"ML Inmuebles: {len(ml_props)} propiedades")
    except Exception as e:
        logger.error(f"Error en scraping ML Inmuebles: {e}")
        await notify_scraping_error("ML Inmuebles", str(e))

    if not all_properties:
        logger.warning("No se encontraron propiedades en ningún portal")
        return 0

    # Filtrar por rango de precio y convertir CLP a UF
    filtered = _filter_and_convert(all_properties, uf_value)
    logger.info(f"Propiedades después de filtro: {len(filtered)}")

    # Guardar en BD
    saved, updated = await _save_properties(filtered)
    logger.info(f"Scraping completado: {saved} nuevas, {updated} actualizadas")

    return saved + updated


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
