"""Estaciones futuras de Metro de Santiago (Líneas 7, 8 y 9).

Datos públicos del proyecto de extensión del Metro.
Fuente: Metro de Santiago / Ministerio de Transportes.
"""
import math

# Línea 7: Renca - Vitacura (aprobada, en construcción)
# Línea 8: Providencia - Puente Alto (en estudio)
# Línea 9: Lo Barnechea - La Cisterna (en estudio)

FUTURE_STATIONS = [
    # Línea 7
    {"line": "L7", "name": "Brasil", "lat": -33.4430, "lng": -70.6580},
    {"line": "L7", "name": "Cumming", "lat": -33.4420, "lng": -70.6640},
    {"line": "L7", "name": "Matucana", "lat": -33.4415, "lng": -70.6720},
    {"line": "L7", "name": "Ñuñoa", "lat": -33.4560, "lng": -70.6100},
    {"line": "L7", "name": "Irarrázaval", "lat": -33.4540, "lng": -70.6200},
    # Línea 8 (estaciones estimadas en zonas de interés)
    {"line": "L8", "name": "San Miguel Sur", "lat": -33.5050, "lng": -70.6520},
    {"line": "L8", "name": "Departamental", "lat": -33.5000, "lng": -70.6500},
    # Línea 9
    {"line": "L9", "name": "Gran Avenida", "lat": -33.4930, "lng": -70.6510},
    {"line": "L9", "name": "Lo Vial", "lat": -33.4900, "lng": -70.6480},
]


def _haversine_meters(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calcula distancia en metros entre dos puntos geográficos."""
    R = 6371000  # Radio de la Tierra en metros
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def find_nearest_future_station(
    lat: float, lng: float, max_distance_m: float = 1500
) -> dict | None:
    """Encuentra la estación futura de Metro más cercana.

    Retorna None si no hay ninguna dentro del radio máximo.
    """
    nearest = None
    min_dist = float("inf")

    for station in FUTURE_STATIONS:
        dist = _haversine_meters(lat, lng, station["lat"], station["lng"])
        if dist < min_dist and dist <= max_distance_m:
            min_dist = dist
            nearest = {
                "line": station["line"],
                "name": station["name"],
                "distance_m": round(dist),
                "walk_minutes": round(dist / 80),  # ~80m/min caminando
            }

    return nearest
