import logging
import re
from datetime import datetime, timezone

from rapidfuzz import fuzz
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import async_session
from app.models.property import Property

logger = logging.getLogger(__name__)

# Mapeo de variantes de nombres de comunas a su forma canónica
COMMUNE_ALIASES = {
    "santiago": "Santiago Centro",
    "santiago centro": "Santiago Centro",
    "stgo centro": "Santiago Centro",
    "stgo": "Santiago Centro",
    "san miguel": "San Miguel",
    "estacion central": "Estación Central",
    "estación central": "Estación Central",
    "est. central": "Estación Central",
    "ñuñoa": "Ñuñoa",
    "nunoa": "Ñuñoa",
}


def normalize_commune(commune: str) -> str | None:
    """Normaliza el nombre de la comuna a su forma canónica.

    Retorna None si no es una comuna objetivo.
    """
    if not commune:
        return None

    key = commune.strip().lower()

    # Búsqueda directa
    if key in COMMUNE_ALIASES:
        return COMMUNE_ALIASES[key]

    # Búsqueda parcial
    for alias, canonical in COMMUNE_ALIASES.items():
        if alias in key or key in alias:
            return canonical

    # Verificar si ya es la forma canónica
    if commune.strip() in settings.target_communes:
        return commune.strip()

    return None


def normalize_price_text(text: str) -> tuple[float | None, str]:
    """Extrae precio y moneda de un texto de precio.

    Retorna (valor, moneda) donde moneda es "UF" o "CLP".
    """
    if not text:
        return None, ""

    text = text.strip().upper()

    # UF
    uf_match = re.search(r"([\d.,]+)\s*UF", text)
    if uf_match:
        try:
            value = float(uf_match.group(1).replace(".", "").replace(",", "."))
            return value, "UF"
        except ValueError:
            pass

    # CLP (pesos)
    clp_match = re.search(r"\$?\s*([\d.,]+)", text)
    if clp_match:
        try:
            raw = clp_match.group(1).replace(".", "").replace(",", "")
            value = float(raw)
            if value > 100_000:  # Probablemente CLP
                return value, "CLP"
        except ValueError:
            pass

    return None, ""


def is_valid_property(prop: Property) -> bool:
    """Verifica que una propiedad tenga los datos mínimos requeridos."""
    if not prop.source_url:
        return False
    if not prop.title:
        return False
    if prop.price_uf is None or prop.price_uf <= 0:
        return False
    if prop.m2_total is None or prop.m2_total <= 0:
        return False
    if prop.commune not in settings.target_communes:
        return False
    return True


def are_duplicates(prop_a: Property, prop_b: Property, threshold: int = 85) -> bool:
    """Detecta si dos propiedades son duplicadas usando fuzzy matching.

    Compara título + dirección + precio + m². Dos propiedades del mismo
    portal con diferente source_id no deberían llegar aquí (se filtran por
    el índice único source+source_id).
    """
    # Si son del mismo portal, no comparar (ya tienen unique constraint)
    if prop_a.source == prop_b.source:
        return False

    # Misma comuna es requisito
    if prop_a.commune != prop_b.commune:
        return False

    # Comparar precio (tolerancia 5%)
    if prop_a.price_uf and prop_b.price_uf:
        price_diff = abs(prop_a.price_uf - prop_b.price_uf) / max(
            prop_a.price_uf, prop_b.price_uf
        )
        if price_diff > 0.05:
            return False

    # Comparar m² (tolerancia 3m²)
    if prop_a.m2_total and prop_b.m2_total:
        if abs(prop_a.m2_total - prop_b.m2_total) > 3:
            return False

    # Fuzzy match en título
    title_score = fuzz.token_sort_ratio(
        prop_a.title.lower(), prop_b.title.lower()
    )

    # Fuzzy match en dirección (si existe)
    addr_score = 0
    if prop_a.address and prop_b.address:
        addr_score = fuzz.token_sort_ratio(
            prop_a.address.lower(), prop_b.address.lower()
        )

    # Score combinado
    if addr_score > 0:
        combined = (title_score * 0.6) + (addr_score * 0.4)
    else:
        combined = title_score

    return combined >= threshold


async def deduplicate_properties():
    """Marca propiedades duplicadas entre portales.

    Mantiene la propiedad con más datos completos y marca
    la otra como inactiva.
    """
    logger.info("Iniciando deduplicación entre portales...")
    dedup_count = 0

    async with async_session() as session:
        for commune in settings.target_communes:
            # Obtener propiedades activas de la comuna
            stmt = (
                select(Property)
                .where(
                    Property.commune == commune,
                    Property.is_active == True,  # noqa: E712
                )
                .order_by(Property.created_at)
            )
            result = await session.execute(stmt)
            props = list(result.scalars().all())

            # Comparar entre portales
            seen: list[Property] = []
            for prop in props:
                is_dup = False
                for existing in seen:
                    if are_duplicates(prop, existing):
                        # Mantener la que tiene más datos
                        keep, discard = _pick_better(existing, prop)
                        if discard.id != existing.id:
                            # Reemplazar en seen
                            seen.remove(existing)
                            seen.append(keep)
                        discard.is_active = False
                        dedup_count += 1
                        is_dup = True
                        logger.debug(
                            f"  Duplicado: {discard.source}:{discard.source_id} "
                            f"= {keep.source}:{keep.source_id}"
                        )
                        break
                if not is_dup:
                    seen.append(prop)

        await session.commit()

    logger.info(f"Deduplicación: {dedup_count} duplicados marcados como inactivos")
    return dedup_count


def _pick_better(a: Property, b: Property) -> tuple[Property, Property]:
    """Elige la propiedad con más datos completos."""
    score_a = _completeness_score(a)
    score_b = _completeness_score(b)
    if score_a >= score_b:
        return a, b
    return b, a


def _completeness_score(prop: Property) -> int:
    """Cuenta cuántos campos opcionales están llenos."""
    score = 0
    if prop.description:
        score += 2
    if prop.address:
        score += 1
    if prop.latitude and prop.longitude:
        score += 2
    if prop.bedrooms is not None:
        score += 1
    if prop.bathrooms is not None:
        score += 1
    if prop.floor is not None:
        score += 1
    if prop.has_parking is not None:
        score += 1
    if prop.has_bodega is not None:
        score += 1
    if prop.building_year is not None:
        score += 1
    if prop.images:
        score += 1
    return score
