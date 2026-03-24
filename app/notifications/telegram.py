import logging
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from app.config import settings
from app.database import async_session
from app.models.alert import Alert
from app.models.feedback import Feedback
from app.models.market_average import MarketAverage
from app.models.notification_log import NotificationLog
from app.models.property import Property
from app.models.user import User

logger = logging.getLogger(__name__)

# Estados de conversación
SELECTING_COMMUNES, SELECTING_PRICE_MIN, SELECTING_PRICE_MAX = range(3)

TARGET_COMMUNES = settings.target_communes


# ===========================================================================
# COMANDOS BÁSICOS
# ===========================================================================


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Registra al usuario y da la bienvenida."""
    chat_id = str(update.effective_chat.id)
    username = update.effective_user.username or ""
    name = update.effective_user.full_name or ""

    async with async_session() as session:
        # Verificar si ya existe
        stmt = select(User).where(User.telegram_chat_id == chat_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if user:
            user.is_active = True
            await session.commit()
            await update.message.reply_text(
                f"Bienvenido de vuelta, {name}.\n\n"
                "Tus alertas están activas nuevamente.\n"
                "Usa /ayuda para ver los comandos disponibles."
            )
        else:
            # Crear usuario
            new_user = User(
                telegram_chat_id=chat_id,
                telegram_username=username,
                name=name,
                is_active=True,
            )
            session.add(new_user)
            await session.flush()

            # Crear alerta por defecto
            default_alert = Alert(
                user_id=new_user.id,
                min_price_uf=settings.min_price_uf,
                max_price_uf=settings.max_price_uf,
                target_communes=TARGET_COMMUNES,
                min_bedrooms=settings.min_bedrooms,
                max_bedrooms=settings.max_bedrooms,
                min_score=settings.opportunity_min_score,
                is_active=True,
            )
            session.add(default_alert)
            await session.commit()

            await update.message.reply_text(
                f"Bienvenido a InmoAlert Chile, {name}.\n\n"
                "Tu cuenta ha sido creada con la configuración por defecto:\n"
                f"  Comunas: {', '.join(TARGET_COMMUNES)}\n"
                f"  Precio: {settings.min_price_uf:,.0f} - {settings.max_price_uf:,.0f} UF\n"
                f"  Dormitorios: {settings.min_bedrooms}-{settings.max_bedrooms}\n"
                f"  Score mínimo: {settings.opportunity_min_score}\n\n"
                "Recibirás alertas automáticas cuando detectemos oportunidades.\n\n"
                "Usa /ayuda para ver todos los comandos."
            )


async def cmd_ayuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra los comandos disponibles."""
    await update.message.reply_text(
        "COMANDOS DISPONIBLES\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "/start - Registrarse / reactivar alertas\n"
        "/comunas - Ver o cambiar comunas de interés\n"
        "/precio - Ver o cambiar rango de precio (UF)\n"
        "/top - Top 5 oportunidades del día\n"
        "/mercado - Promedios UF/m² por comuna\n"
        "/mi_config - Ver tu configuración actual\n"
        "/feedback - Evaluar oportunidades recibidas\n"
        "/stop - Pausar notificaciones\n"
        "/ayuda - Este mensaje\n"
    )


async def cmd_stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Pausa las notificaciones del usuario."""
    chat_id = str(update.effective_chat.id)

    async with async_session() as session:
        stmt = select(User).where(User.telegram_chat_id == chat_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if user:
            user.is_active = False
            await session.commit()
            await update.message.reply_text(
                "Notificaciones pausadas.\n"
                "Usa /start para reactivarlas."
            )
        else:
            await update.message.reply_text(
                "No estás registrado. Usa /start primero."
            )


async def cmd_mi_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra la configuración actual del usuario."""
    chat_id = str(update.effective_chat.id)

    async with async_session() as session:
        user = await _get_user(session, chat_id)
        if not user:
            await update.message.reply_text("No estás registrado. Usa /start primero.")
            return

        alert = await _get_user_alert(session, user.id)
        if not alert:
            await update.message.reply_text("No tienes alertas configuradas.")
            return

        communes = alert.target_communes or []
        await update.message.reply_text(
            "TU CONFIGURACIÓN\n"
            "━━━━━━━━━━━━━━━━\n\n"
            f"Comunas: {', '.join(communes)}\n"
            f"Precio: {float(alert.min_price_uf):,.0f} - {float(alert.max_price_uf):,.0f} UF\n"
            f"Dormitorios: {alert.min_bedrooms}-{alert.max_bedrooms}\n"
            f"Score mínimo: {alert.min_score}\n"
            f"Estado: {'Activo' if user.is_active else 'Pausado'}\n"
            f"Alertas enviadas: {user.notifications_sent}\n"
        )


# ===========================================================================
# COMANDOS DE PREFERENCIAS
# ===========================================================================


async def cmd_comunas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra teclado inline para seleccionar comunas."""
    chat_id = str(update.effective_chat.id)

    async with async_session() as session:
        user = await _get_user(session, chat_id)
        if not user:
            await update.message.reply_text("No estás registrado. Usa /start primero.")
            return

        alert = await _get_user_alert(session, user.id)
        current = alert.target_communes if alert else []

    keyboard = []
    for commune in TARGET_COMMUNES:
        check = " [X]" if commune in current else ""
        keyboard.append(
            [InlineKeyboardButton(f"{commune}{check}", callback_data=f"commune:{commune}")]
        )
    keyboard.append(
        [InlineKeyboardButton("Confirmar", callback_data="commune:confirm")]
    )

    await update.message.reply_text(
        "Selecciona las comunas de interés\n(toca para agregar/quitar):",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def callback_commune(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja la selección de comunas via botones inline."""
    query = update.callback_query
    await query.answer()

    chat_id = str(query.message.chat_id)
    data = query.data.replace("commune:", "")

    async with async_session() as session:
        user = await _get_user(session, chat_id)
        if not user:
            return

        alert = await _get_user_alert(session, user.id)
        if not alert:
            return

        current = list(alert.target_communes or [])

        if data == "confirm":
            if not current:
                await query.edit_message_text("Debes seleccionar al menos una comuna.")
                return
            alert.target_communes = current
            await session.commit()
            await query.edit_message_text(
                f"Comunas actualizadas: {', '.join(current)}"
            )
            return

        # Toggle comuna
        if data in current:
            current.remove(data)
        else:
            current.append(data)

        alert.target_communes = current
        await session.commit()

    # Actualizar teclado
    keyboard = []
    for commune in TARGET_COMMUNES:
        check = " [X]" if commune in current else ""
        keyboard.append(
            [InlineKeyboardButton(f"{commune}{check}", callback_data=f"commune:{commune}")]
        )
    keyboard.append(
        [InlineKeyboardButton("Confirmar", callback_data="commune:confirm")]
    )

    await query.edit_message_text(
        "Selecciona las comunas de interés\n(toca para agregar/quitar):",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def cmd_precio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inicia la configuración de rango de precio."""
    chat_id = str(update.effective_chat.id)

    async with async_session() as session:
        user = await _get_user(session, chat_id)
        if not user:
            await update.message.reply_text("No estás registrado. Usa /start primero.")
            return

    await update.message.reply_text(
        "Ingresa el precio MÍNIMO en UF (ej: 1500):"
    )
    return SELECTING_PRICE_MIN


async def receive_price_min(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recibe el precio mínimo."""
    try:
        min_uf = float(update.message.text.strip().replace(".", "").replace(",", "."))
        if min_uf < 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("Ingresa un número válido (ej: 1500):")
        return SELECTING_PRICE_MIN

    context.user_data["min_uf"] = min_uf
    await update.message.reply_text(
        f"Mínimo: {min_uf:,.0f} UF\n\n"
        "Ahora ingresa el precio MÁXIMO en UF (ej: 4000):"
    )
    return SELECTING_PRICE_MAX


async def receive_price_max(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recibe el precio máximo y guarda."""
    try:
        max_uf = float(update.message.text.strip().replace(".", "").replace(",", "."))
        if max_uf < 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("Ingresa un número válido (ej: 4000):")
        return SELECTING_PRICE_MAX

    min_uf = context.user_data.get("min_uf", 1500)

    if max_uf <= min_uf:
        await update.message.reply_text(
            f"El máximo ({max_uf:,.0f}) debe ser mayor al mínimo ({min_uf:,.0f}).\n"
            "Ingresa el precio MÁXIMO en UF:"
        )
        return SELECTING_PRICE_MAX

    chat_id = str(update.effective_chat.id)

    async with async_session() as session:
        user = await _get_user(session, chat_id)
        if user:
            alert = await _get_user_alert(session, user.id)
            if alert:
                alert.min_price_uf = min_uf
                alert.max_price_uf = max_uf
                await session.commit()

    await update.message.reply_text(
        f"Rango de precio actualizado: {min_uf:,.0f} - {max_uf:,.0f} UF"
    )
    return ConversationHandler.END


async def cancel_precio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancela la configuración de precio."""
    await update.message.reply_text("Configuración de precio cancelada.")
    return ConversationHandler.END


async def cmd_top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra las top 5 oportunidades del día."""
    chat_id = str(update.effective_chat.id)

    async with async_session() as session:
        user = await _get_user(session, chat_id)
        if not user:
            await update.message.reply_text("No estás registrado. Usa /start primero.")
            return

        alert = await _get_user_alert(session, user.id)
        communes = alert.target_communes if alert else TARGET_COMMUNES

        stmt = (
            select(Property)
            .where(
                Property.is_opportunity == True,  # noqa: E712
                Property.is_active == True,  # noqa: E712
                Property.commune.in_(communes),
            )
            .order_by(Property.opportunity_score.desc())
            .limit(5)
        )
        result = await session.execute(stmt)
        props = list(result.scalars().all())

        # Cargar promedios
        averages = await _load_averages(session)

    if not props:
        await update.message.reply_text(
            "No hay oportunidades disponibles en este momento.\n"
            "El sistema busca cada 4 horas."
        )
        return

    text = "TOP 5 OPORTUNIDADES\n━━━━━━━━━━━━━━━━━━━━\n\n"
    for i, p in enumerate(props, 1):
        text += _format_opportunity_short(i, p, averages)
        text += "\n"

    await update.message.reply_text(text, disable_web_page_preview=True)


async def cmd_mercado(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra promedios de mercado por comuna."""
    async with async_session() as session:
        stmt = select(MarketAverage).order_by(
            MarketAverage.commune, MarketAverage.bedrooms
        )
        result = await session.execute(stmt)
        averages = list(result.scalars().all())

    if not averages:
        await update.message.reply_text(
            "Aún no hay datos de mercado.\n"
            "El sistema necesita recopilar propiedades primero."
        )
        return

    text = "PROMEDIOS DE MERCADO (UF/m²)\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    current_commune = ""
    for ma in averages:
        if ma.commune != current_commune:
            current_commune = ma.commune
            text += f"{ma.commune}\n"
        text += (
            f"  {ma.bedrooms}D: "
            f"avg {float(ma.avg_price_m2_uf):.1f} | "
            f"med {float(ma.median_price_m2_uf):.1f} | "
            f"n={ma.sample_count}\n"
        )

    await update.message.reply_text(text)


# ===========================================================================
# FORMATO DE MENSAJES DE ALERTA
# ===========================================================================


def format_opportunity_alert(prop: Property, avg_price_m2: float | None) -> str:
    """Formatea una oportunidad para enviar como alerta por Telegram."""
    # Clasificación por score
    score = prop.opportunity_score or 0
    if score >= 80:
        badge = "ORO"
        emoji_score = "***"
    elif score >= 60:
        badge = "PLATA"
        emoji_score = "**"
    else:
        badge = "BRONCE"
        emoji_score = "*"

    # % bajo mercado
    pct_below = ""
    estimated = ""
    if avg_price_m2 and prop.price_m2_uf:
        pct = ((float(prop.price_m2_uf) - avg_price_m2) / avg_price_m2) * 100
        pct_below = f"{pct:+.1f}% vs mercado"
        if prop.m2_total:
            est_value = avg_price_m2 * float(prop.m2_total)
            estimated = f"Valor mercado: {est_value:,.0f} UF"

    price_text = f"{float(prop.price_uf):,.0f} UF" if prop.price_uf else "N/D"
    m2_text = f"{float(prop.m2_total):.0f} m²" if prop.m2_total else "N/D"
    price_m2_text = f"{float(prop.price_m2_uf):.1f} UF/m²" if prop.price_m2_uf else ""
    beds = f"{prop.bedrooms}D" if prop.bedrooms else ""
    baths = f"{prop.bathrooms}B" if prop.bathrooms else ""
    layout = f" | {beds}" + (f" {baths}" if baths else "")

    parking = "Si" if prop.has_parking else ("No" if prop.has_parking is False else "N/D")

    lines = [
        f"OPORTUNIDAD {badge} (Score: {score}) {emoji_score}",
        "━━━━━━━━━━━━━━━━━━━━━━━━",
        f"Comuna: {prop.commune}",
        f"Precio: {price_text}",
    ]

    if pct_below:
        lines.append(f"Mercado: {pct_below}")
    if estimated:
        lines.append(f"{estimated}")

    lines.append(f"Superficie: {m2_text}{layout}")

    if price_m2_text:
        avg_text = f" (prom: {avg_price_m2:.1f})" if avg_price_m2 else ""
        lines.append(f"UF/m²: {price_m2_text}{avg_text}")

    lines.append(f"Estacionamiento: {parking}")

    if prop.has_urgency_keyword:
        lines.append("Tiene keywords de urgencia")

    lines.append("")
    lines.append(f"Ver anuncio: {prop.source_url}")

    return "\n".join(lines)


def _format_opportunity_short(
    rank: int, prop: Property, averages: dict
) -> str:
    """Formato corto para listado /top."""
    key = (prop.commune, prop.bedrooms)
    avg = averages.get(key)
    avg_m2 = float(avg.avg_price_m2_uf) if avg else None

    pct = ""
    if avg_m2 and prop.price_m2_uf:
        p = ((float(prop.price_m2_uf) - avg_m2) / avg_m2) * 100
        pct = f" ({p:+.0f}%)"

    price = f"{float(prop.price_uf):,.0f}" if prop.price_uf else "?"
    m2 = f"{float(prop.m2_total):.0f}m²" if prop.m2_total else "?"
    beds = f"{prop.bedrooms}D" if prop.bedrooms else ""
    score = prop.opportunity_score or 0

    return (
        f"{rank}. [{score}pts] {prop.commune}\n"
        f"   {price} UF | {m2} | {beds}{pct}\n"
        f"   {prop.source_url}\n"
    )


# ===========================================================================
# SISTEMA DE ALERTAS PUSH
# ===========================================================================


async def send_opportunity_alerts(properties: list[Property]):
    """Envía alertas de oportunidades a usuarios que coincidan con sus preferencias.

    Reglas:
    - Solo usuarios activos
    - Solo oportunidades con score >= min_score del usuario
    - Máximo MAX_ALERTS_PER_DAY por usuario por día
    - No enviar la misma propiedad dos veces al mismo usuario
    - Horario: 08:00 - 22:00 CLT (UTC-3 / UTC-4)
    """
    if not properties:
        return 0

    if not settings.telegram_bot_token:
        logger.warning("TELEGRAM_BOT_TOKEN no configurado. No se envían alertas.")
        return 0

    bot = Bot(token=settings.telegram_bot_token)
    total_sent = 0

    async with async_session() as session:
        # Cargar promedios de mercado
        averages = await _load_averages(session)

        # Obtener usuarios activos con sus alertas
        stmt = (
            select(User, Alert)
            .join(Alert, Alert.user_id == User.id)
            .where(
                User.is_active == True,  # noqa: E712
                Alert.is_active == True,  # noqa: E712
            )
        )
        result = await session.execute(stmt)
        user_alerts = list(result.all())

        if not user_alerts:
            logger.info("No hay usuarios activos con alertas")
            return 0

        for prop in properties:
            for user, alert in user_alerts:
                should_send = await _should_send_alert(
                    session, user, alert, prop
                )
                if not should_send:
                    continue

                # Obtener promedio de la zona
                key = (prop.commune, prop.bedrooms)
                avg = averages.get(key)
                avg_m2 = float(avg.avg_price_m2_uf) if avg else None

                # Formatear y enviar
                message = format_opportunity_alert(prop, avg_m2)
                sent = await _send_telegram_message(
                    bot, user.telegram_chat_id, message
                )

                if sent:
                    # Registrar en notification_log
                    log = NotificationLog(
                        user_id=user.id,
                        property_id=prop.id,
                        channel="telegram",
                        status="sent",
                    )
                    session.add(log)
                    user.notifications_sent = (user.notifications_sent or 0) + 1
                    user.last_notified_at = datetime.now(timezone.utc)
                    total_sent += 1

        await session.commit()

    logger.info(f"Alertas enviadas: {total_sent}")
    return total_sent


async def _should_send_alert(
    session: AsyncSession, user: User, alert: Alert, prop: Property
) -> bool:
    """Verifica si se debe enviar una alerta a un usuario para una propiedad."""
    # Verificar score mínimo
    if (prop.opportunity_score or 0) < (alert.min_score or 0):
        return False

    # Verificar comuna
    target_communes = alert.target_communes or []
    if target_communes and prop.commune not in target_communes:
        return False

    # Verificar rango de precio
    if prop.price_uf:
        price = float(prop.price_uf)
        if alert.min_price_uf and price < float(alert.min_price_uf):
            return False
        if alert.max_price_uf and price > float(alert.max_price_uf):
            return False

    # Verificar dormitorios
    if prop.bedrooms:
        if alert.min_bedrooms and prop.bedrooms < alert.min_bedrooms:
            return False
        if alert.max_bedrooms and prop.bedrooms > alert.max_bedrooms:
            return False

    # Verificar que no se haya notificado antes
    stmt = select(NotificationLog).where(
        NotificationLog.user_id == user.id,
        NotificationLog.property_id == prop.id,
    )
    result = await session.execute(stmt)
    if result.scalar_one_or_none():
        return False

    # Verificar límite diario
    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    stmt = (
        select(func.count())
        .select_from(NotificationLog)
        .where(
            NotificationLog.user_id == user.id,
            NotificationLog.sent_at >= today_start,
        )
    )
    result = await session.execute(stmt)
    today_count = result.scalar() or 0

    if today_count >= settings.max_alerts_per_day:
        return False

    return True


async def _send_telegram_message(bot: Bot, chat_id: str, text: str) -> bool:
    """Envía un mensaje por Telegram. Retorna True si fue exitoso."""
    try:
        await bot.send_message(
            chat_id=chat_id,
            text=text,
            disable_web_page_preview=True,
        )
        return True
    except Exception as e:
        logger.error(f"Error enviando mensaje a {chat_id}: {e}")
        return False


# ===========================================================================
# FEEDBACK DE USUARIOS
# ===========================================================================


async def cmd_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra las últimas oportunidades notificadas para dar feedback."""
    chat_id = str(update.effective_chat.id)

    async with async_session() as session:
        user = await _get_user(session, chat_id)
        if not user:
            await update.message.reply_text("No estás registrado. Usa /start primero.")
            return

        # Últimas 5 propiedades notificadas al usuario
        stmt = (
            select(NotificationLog, Property)
            .join(Property, NotificationLog.property_id == Property.id)
            .where(NotificationLog.user_id == user.id)
            .order_by(NotificationLog.sent_at.desc())
            .limit(5)
        )
        result = await session.execute(stmt)
        rows = list(result.all())

    if not rows:
        await update.message.reply_text(
            "Aún no has recibido alertas para evaluar."
        )
        return

    keyboard = []
    for notif, prop in rows:
        price = f"{float(prop.price_uf):,.0f}UF" if prop.price_uf else "?"
        label = f"{prop.commune} | {price} | Score:{prop.opportunity_score}"
        keyboard.append([
            InlineKeyboardButton(
                f"Buena: {label}", callback_data=f"fb:good:{prop.id}"
            ),
        ])
        keyboard.append([
            InlineKeyboardButton(
                f"Mala: {label}", callback_data=f"fb:bad:{prop.id}"
            ),
        ])

    await update.message.reply_text(
        "Evalúa las últimas oportunidades que recibiste.\n"
        "Tu feedback nos ayuda a mejorar la detección:\n",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def callback_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Procesa el feedback del usuario sobre una oportunidad."""
    query = update.callback_query
    await query.answer()

    chat_id = str(query.message.chat_id)
    parts = query.data.split(":")
    if len(parts) != 3:
        return

    _, quality, property_id = parts
    is_good = quality == "good"

    # Validar UUID
    try:
        import uuid as uuid_mod
        uuid_mod.UUID(property_id)
    except ValueError:
        logger.warning(f"Invalid property_id in feedback: {property_id}")
        return

    async with async_session() as session:
        user = await _get_user(session, chat_id)
        if not user:
            return

        # Upsert atómico — evita race condition
        from sqlalchemy.dialects.postgresql import insert as pg_insert
        stmt = pg_insert(Feedback).values(
            user_id=user.id,
            property_id=property_id,
            is_good=is_good,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["user_id", "property_id"],
            set_={"is_good": is_good},
        )
        await session.execute(stmt)
        await session.commit()

    label = "BUENA" if is_good else "MALA"
    await query.edit_message_text(
        f"Feedback registrado: oportunidad marcada como {label}.\n"
        "Gracias, esto nos ayuda a mejorar."
    )


# ===========================================================================
# HELPERS
# ===========================================================================


async def _get_user(session: AsyncSession, chat_id: str) -> User | None:
    stmt = select(User).where(User.telegram_chat_id == chat_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def _get_user_alert(session: AsyncSession, user_id) -> Alert | None:
    stmt = select(Alert).where(Alert.user_id == user_id, Alert.is_active == True)  # noqa: E712
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def _load_averages(session: AsyncSession) -> dict:
    stmt = select(MarketAverage)
    result = await session.execute(stmt)
    return {
        (ma.commune, ma.bedrooms): ma for ma in result.scalars().all()
    }


# ===========================================================================
# CONFIGURAR BOT
# ===========================================================================


def build_telegram_app() -> Application | None:
    """Construye la aplicación de Telegram con todos los handlers."""
    if not settings.telegram_bot_token:
        logger.warning("TELEGRAM_BOT_TOKEN no configurado. Bot deshabilitado.")
        return None

    app = Application.builder().token(settings.telegram_bot_token).build()

    # Comandos básicos
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("ayuda", cmd_ayuda))
    app.add_handler(CommandHandler("help", cmd_ayuda))
    app.add_handler(CommandHandler("stop", cmd_stop))
    app.add_handler(CommandHandler("mi_config", cmd_mi_config))

    # Comandos de datos
    app.add_handler(CommandHandler("comunas", cmd_comunas))
    app.add_handler(CommandHandler("top", cmd_top))
    app.add_handler(CommandHandler("mercado", cmd_mercado))

    # Feedback
    app.add_handler(CommandHandler("feedback", cmd_feedback))

    # Callbacks para botones inline
    app.add_handler(CallbackQueryHandler(callback_commune, pattern=r"^commune:"))
    app.add_handler(CallbackQueryHandler(callback_feedback, pattern=r"^fb:"))

    # Conversación para precio (requiere múltiples pasos)
    precio_handler = ConversationHandler(
        entry_points=[CommandHandler("precio", cmd_precio)],
        states={
            SELECTING_PRICE_MIN: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_price_min)
            ],
            SELECTING_PRICE_MAX: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_price_max)
            ],
        },
        fallbacks=[CommandHandler("cancelar", cancel_precio)],
    )
    app.add_handler(precio_handler)

    return app
