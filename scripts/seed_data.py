"""Script para insertar datos de prueba en la BD y ver el frontend funcionando."""
import asyncio
import random
import uuid
from datetime import datetime, timedelta, timezone

from app.config import settings
from app.database import async_session, init_db
from app.models.property import Property
from app.models.market_average import MarketAverage
from app.analysis.scoring import calculate_score, detect_urgency_keywords

# Datos realistas de departamentos en Santiago
SAMPLE_PROPERTIES = [
    # Santiago Centro - 1D
    {"title": "Depto 1D nuevo metro U de Chile", "commune": "Santiago Centro", "bedrooms": 1, "bathrooms": 1, "m2": 35, "price_uf": 1850, "address": "San Antonio 456", "parking": False, "bodega": False},
    {"title": "URGENTE vendo depto amoblado centro", "commune": "Santiago Centro", "bedrooms": 1, "bathrooms": 1, "m2": 32, "price_uf": 1600, "address": "Morandé 312", "parking": False, "bodega": False},
    {"title": "Depto 1D vista panorámica Alameda", "commune": "Santiago Centro", "bedrooms": 1, "bathrooms": 1, "m2": 40, "price_uf": 2200, "address": "Av. Libertador Bernardo O'Higgins 1500", "parking": True, "bodega": False},
    {"title": "Studio moderno barrio Lastarria", "commune": "Santiago Centro", "bedrooms": 1, "bathrooms": 1, "m2": 28, "price_uf": 1750, "address": "José Victorino Lastarria 70", "parking": False, "bodega": False},
    {"title": "Depto conversable cerca metro Santa Lucía", "commune": "Santiago Centro", "bedrooms": 1, "bathrooms": 1, "m2": 38, "price_uf": 1700, "address": "Merced 842", "parking": False, "bodega": True},
    # Santiago Centro - 2D
    {"title": "Depto 2D 1B edificio nuevo Santiago", "commune": "Santiago Centro", "bedrooms": 2, "bathrooms": 1, "m2": 52, "price_uf": 2800, "address": "Compañía de Jesús 1320", "parking": True, "bodega": True},
    {"title": "Remate depto 2 dormitorios centro", "commune": "Santiago Centro", "bedrooms": 2, "bathrooms": 1, "m2": 48, "price_uf": 2100, "address": "Teatinos 240", "parking": False, "bodega": False},
    {"title": "Depto 2D luminoso metro Moneda", "commune": "Santiago Centro", "bedrooms": 2, "bathrooms": 2, "m2": 55, "price_uf": 3200, "address": "Moneda 1150", "parking": True, "bodega": True},
    {"title": "Oportunidad depto familiar centro", "commune": "Santiago Centro", "bedrooms": 2, "bathrooms": 1, "m2": 50, "price_uf": 2400, "address": "Huérfanos 786", "parking": False, "bodega": False},
    # San Miguel - 1D
    {"title": "Depto 1D San Miguel metro", "commune": "San Miguel", "bedrooms": 1, "bathrooms": 1, "m2": 36, "price_uf": 1900, "address": "Gran Avenida 5400", "parking": True, "bodega": False},
    {"title": "Depto sin comisión San Miguel", "commune": "San Miguel", "bedrooms": 1, "bathrooms": 1, "m2": 33, "price_uf": 1550, "address": "Salesianos 1230", "parking": False, "bodega": False},
    {"title": "Departamento 1D nuevo Lo Vial", "commune": "San Miguel", "bedrooms": 1, "bathrooms": 1, "m2": 38, "price_uf": 2000, "address": "Lo Vial 580", "parking": True, "bodega": True},
    # San Miguel - 2D
    {"title": "Depto 2D San Miguel excelente ubicación", "commune": "San Miguel", "bedrooms": 2, "bathrooms": 1, "m2": 50, "price_uf": 2600, "address": "Gran Avenida 4850", "parking": True, "bodega": True},
    {"title": "Liquidación depto 2D San Miguel sur", "commune": "San Miguel", "bedrooms": 2, "bathrooms": 1, "m2": 46, "price_uf": 2050, "address": "Departamental 1456", "parking": False, "bodega": False},
    {"title": "Depto 2D cerca metro San Miguel", "commune": "San Miguel", "bedrooms": 2, "bathrooms": 2, "m2": 55, "price_uf": 3100, "address": "Alcalde Pedro Alarcón 940", "parking": True, "bodega": True},
    # Estación Central - 1D
    {"title": "Depto 1D Estación Central económico", "commune": "Estación Central", "bedrooms": 1, "bathrooms": 1, "m2": 30, "price_uf": 1500, "address": "Av. Ecuador 4230", "parking": False, "bodega": False},
    {"title": "Necesito vender depto Est Central", "commune": "Estación Central", "bedrooms": 1, "bathrooms": 1, "m2": 34, "price_uf": 1580, "address": "Las Rejas Sur 1100", "parking": False, "bodega": False},
    {"title": "Depto 1D nuevo metro Las Rejas", "commune": "Estación Central", "bedrooms": 1, "bathrooms": 1, "m2": 36, "price_uf": 1800, "address": "Av. Las Rejas Norte 560", "parking": True, "bodega": False},
    # Estación Central - 2D
    {"title": "Depto 2D ganga Estación Central", "commune": "Estación Central", "bedrooms": 2, "bathrooms": 1, "m2": 48, "price_uf": 2100, "address": "Av. Libertador Bernardo O'Higgins 3920", "parking": False, "bodega": False},
    {"title": "Depto 2D Estación Central con est.", "commune": "Estación Central", "bedrooms": 2, "bathrooms": 1, "m2": 52, "price_uf": 2700, "address": "5 de Abril 3456", "parking": True, "bodega": True},
    # Ñuñoa - 1D
    {"title": "Depto 1D Ñuñoa Irarrázaval", "commune": "Ñuñoa", "bedrooms": 1, "bathrooms": 1, "m2": 38, "price_uf": 2300, "address": "Av. Irarrázaval 2580", "parking": True, "bodega": False},
    {"title": "Depto 1D precio rebajado Ñuñoa", "commune": "Ñuñoa", "bedrooms": 1, "bathrooms": 1, "m2": 35, "price_uf": 1900, "address": "Manuel Montt 280", "parking": False, "bodega": False},
    {"title": "Depto 1D luminoso Plaza Ñuñoa", "commune": "Ñuñoa", "bedrooms": 1, "bathrooms": 1, "m2": 40, "price_uf": 2500, "address": "Jorge Washington 150", "parking": True, "bodega": True},
    {"title": "Apurado vendo depto Ñuñoa", "commune": "Ñuñoa", "bedrooms": 1, "bathrooms": 1, "m2": 33, "price_uf": 1800, "address": "Chile España 1200", "parking": False, "bodega": False},
    # Ñuñoa - 2D
    {"title": "Depto 2D Ñuñoa familiar excelente", "commune": "Ñuñoa", "bedrooms": 2, "bathrooms": 2, "m2": 60, "price_uf": 3500, "address": "Av. Irarrázaval 3200", "parking": True, "bodega": True},
    {"title": "Depto 2D bajo avalúo Ñuñoa", "commune": "Ñuñoa", "bedrooms": 2, "bathrooms": 1, "m2": 50, "price_uf": 2400, "address": "Suecia 456", "parking": False, "bodega": False},
    {"title": "Oportunidad 2D Ñuñoa metro", "commune": "Ñuñoa", "bedrooms": 2, "bathrooms": 1, "m2": 53, "price_uf": 2800, "address": "Av. Grecia 890", "parking": True, "bodega": False},
    {"title": "Depto 2D Ñuñoa con vista", "commune": "Ñuñoa", "bedrooms": 2, "bathrooms": 2, "m2": 58, "price_uf": 3800, "address": "Los Leones 1500", "parking": True, "bodega": True},
]


async def seed():
    await init_db()
    now = datetime.now(timezone.utc)

    async with async_session() as session:
        # Insertar propiedades
        properties = []
        for i, data in enumerate(SAMPLE_PROPERTIES):
            hours_ago = random.randint(1, 48)
            source = random.choice(["portal_inmobiliario", "yapo"])
            price_m2 = round(data["price_uf"] / data["m2"], 2)

            prop = Property(
                source=source,
                source_id=f"SEED-{i+1:04d}",
                source_url=f"https://www.portalinmobiliario.com/MLC-{random.randint(1000000, 9999999)}",
                title=data["title"],
                description=f"Departamento de {data['bedrooms']} dormitorio(s) en {data['commune']}. {data['m2']} m² totales.",
                price_uf=data["price_uf"],
                price_m2_uf=price_m2,
                m2_total=data["m2"],
                bedrooms=data["bedrooms"],
                bathrooms=data["bathrooms"],
                commune=data["commune"],
                address=data["address"],
                has_parking=data["parking"],
                has_bodega=data["bodega"],
                is_active=True,
                first_seen_at=now - timedelta(hours=hours_ago),
                last_seen_at=now,
                created_at=now - timedelta(hours=hours_ago),
                updated_at=now,
            )
            session.add(prop)
            properties.append(prop)

        await session.flush()

        # Calcular promedios por zona
        from collections import defaultdict
        import numpy as np

        zone_prices: dict[tuple, list] = defaultdict(list)
        for prop in properties:
            key = (prop.commune, prop.bedrooms)
            zone_prices[key].append(float(prop.price_m2_uf))

        for (commune, bedrooms), prices in zone_prices.items():
            arr = np.array(prices)
            avg = MarketAverage(
                commune=commune,
                bedrooms=bedrooms,
                avg_price_m2_uf=float(np.mean(arr)),
                median_price_m2_uf=float(np.median(arr)),
                min_price_m2_uf=float(np.min(arr)),
                max_price_m2_uf=float(np.max(arr)),
                std_deviation=float(np.std(arr)),
                sample_count=len(arr),
                last_updated=now,
            )
            session.add(avg)

        await session.flush()

        # Calcular scores
        avg_stmt = {}
        for (commune, bedrooms), prices in zone_prices.items():
            avg_stmt[(commune, bedrooms)] = float(np.mean(prices))

        for prop in properties:
            key = (prop.commune, prop.bedrooms)
            avg_m2 = avg_stmt.get(key, 0)
            if avg_m2 > 0:
                keywords = detect_urgency_keywords(prop.title, prop.description)
                prop.has_urgency_keyword = len(keywords) > 0
                prop.opportunity_score = calculate_score(prop, avg_m2)
                deviation = ((float(prop.price_m2_uf) - avg_m2) / avg_m2) * 100
                prop.is_opportunity = (
                    deviation <= settings.price_deviation_threshold
                    or (prop.has_urgency_keyword and deviation <= -10)
                )

        await session.commit()
        print(f"Insertadas {len(properties)} propiedades")
        print(f"Promedios: {len(zone_prices)} zonas")
        opps = sum(1 for p in properties if p.is_opportunity)
        print(f"Oportunidades detectadas: {opps}")


if __name__ == "__main__":
    asyncio.run(seed())
