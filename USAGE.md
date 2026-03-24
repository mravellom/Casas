# InmoAlert Chile - Guía de Uso

## Requisitos

- Python 3.11+
- Docker y Docker Compose
- Cuenta de Telegram (para el bot)

## Setup Rápido

### 1. Clonar y configurar entorno

```bash
cd /home/fabian/workSpace/Casas
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium --with-deps
```

### 2. Configurar variables de entorno

```bash
cp .env.example .env
```

Editar `.env` con tus valores:

```
DATABASE_URL=postgresql+asyncpg://inmoalert:inmoalert_pass@localhost:5432/inmoalert
TELEGRAM_BOT_TOKEN=tu_token_aqui
TELEGRAM_ADMIN_CHAT_ID=tu_chat_id_aqui
```

### 3. Crear bot de Telegram

1. Abrir Telegram y buscar `@BotFather`
2. Enviar `/newbot`
3. Nombre: `InmoAlert Chile`
4. Username: `inmoalert_chile_bot` (o uno disponible)
5. Copiar el token en `.env`

Para obtener tu `TELEGRAM_ADMIN_CHAT_ID`:
1. Buscar `@userinfobot` en Telegram
2. Enviar `/start`
3. Copiar tu Chat ID

### 4. Levantar base de datos

```bash
docker-compose up -d db redis
```

### 5. Iniciar la aplicación

```bash
source venv/bin/activate
uvicorn app.main:app --reload
```

La API estará en `http://localhost:8000`
Documentación Swagger: `http://localhost:8000/docs`

## Uso del Bot de Telegram

Los usuarios interactúan con el bot usando estos comandos:

| Comando | Descripción |
|---------|-------------|
| `/start` | Registrarse y activar alertas |
| `/comunas` | Seleccionar comunas de interés |
| `/precio` | Configurar rango de precio en UF |
| `/top` | Ver las 5 mejores oportunidades |
| `/mercado` | Ver promedios UF/m² por comuna |
| `/mi_config` | Ver configuración actual |
| `/feedback` | Evaluar oportunidades recibidas |
| `/stop` | Pausar notificaciones |
| `/ayuda` | Lista de comandos |

## Invitar Usuarios Beta

1. Compartir el link del bot: `t.me/tu_bot_username`
2. El usuario envía `/start` y queda registrado
3. Se crean preferencias por defecto (4 comunas, 1500-4000 UF)
4. El usuario recibe alertas automáticas cuando hay oportunidades

## API Endpoints

### Propiedades
- `GET /api/v1/properties` - Listar (filtros: commune, min_uf, max_uf, bedrooms)
- `GET /api/v1/properties/{id}` - Detalle

### Oportunidades
- `GET /api/v1/opportunities` - Listar oportunidades (filtros: commune, min_score)
- `GET /api/v1/opportunities/top` - Top oportunidades
- `GET /api/v1/opportunities/market` - Promedios de mercado

### Admin
- `POST /api/v1/admin/scrape/trigger` - Ejecutar pipeline manualmente
- `GET /api/v1/admin/scrape/status` - Estado del pipeline
- `GET /api/v1/admin/health` - Health check
- `GET /api/v1/admin/metrics` - Métricas del sistema
- `GET /api/v1/admin/logs` - Historial de ejecuciones
- `GET /api/v1/admin/feedback/stats` - Tasa de falsos positivos

## Pipeline Automático

El sistema ejecuta automáticamente cada 4 horas:

1. **Scraping** - Extrae deptos de Portal Inmobiliario y Yapo
2. **Deduplicación** - Elimina duplicados entre portales
3. **Pricing** - Recalcula promedios UF/m² por comuna
4. **Scoring** - Calcula score de oportunidad (0-100)
5. **Alertas** - Envía notificaciones por Telegram
6. **Limpieza** - Marca propiedades no vistas en 48h como inactivas

Para ejecutar manualmente:
```bash
curl -X POST http://localhost:8000/api/v1/admin/scrape/trigger
```

## Monitoreo

El admin recibe alertas por Telegram cuando:
- Un scraper falla
- No se encuentran propiedades
- El pipeline tiene errores

Métricas disponibles en: `GET /api/v1/admin/metrics`

## Tests

```bash
source venv/bin/activate
python -m pytest tests/ -v
```

## Criterios de Oportunidad

Una propiedad se marca como oportunidad cuando:
- Precio UF/m² está **>15% por debajo** del promedio de la comuna, O
- Tiene **keywords de urgencia** + precio >10% bajo el promedio

Keywords: urgente, remate, conversable, sin comisión, liquidación, oportunidad, bajo avalúo, precio rebajado, necesito vender, apurado, ganga

## Validación con Usuarios

Objetivo: probar con 5 usuarios reales y alcanzar **<30% de falsos positivos**.

1. Invitar usuarios beta
2. Revisar feedback en `/api/v1/admin/feedback/stats`
3. Ajustar `PRICE_DEVIATION_THRESHOLD` y `OPPORTUNITY_MIN_SCORE` según resultados
4. Si FP > 30%, subir el threshold o ajustar pesos del scoring
