import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    CommandHandler,
    CallbackQueryHandler,
)

from app.bots.funding_bot.utils import with_menu_button

from app.bots.funding_bot.queries.simulation import (
    get_user_simulations,
    get_profile_summary,
    get_user_simulation_detail,
)
from app.bots.funding_bot.formatters.simulation_fmt import (
    format_profile_summary,
    format_simulation_list,
    format_simulation_summary,
)

logger = logging.getLogger(__name__)

# Клавиатуры

def _simulations_keyboard(simulations) -> InlineKeyboardMarkup:
    """Кнопка на каждую симуляцию — для детализации."""
    buttons = []
    for sim in simulations:
        label = (
            f"{sim['symbol']} "
            f"{sim['notional_usdt']:,.0f}$ "
            f"{sim['total_pnl']:+.2f} "
            f"{sim['days']}d"
        )
        buttons.append([
            InlineKeyboardButton(
                label,
                callback_data=f"profile_detail:{sim['id']}",
            )
        ])

    buttons.append([
        InlineKeyboardButton("🔁 Обновить", callback_data="profile_refresh"),
    ])

    return InlineKeyboardMarkup(buttons)


def _detail_keyboard(sim_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🗑 Удалить",
                callback_data=f"profile_delete:{sim_id}",
            ),
            InlineKeyboardButton(
                "◀️ Назад",
                callback_data="profile_back",
            ),
        ]
        
    ])

# Клавиатура подтверждения удаления
def _confirm_delete_keyboard(sim_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(
            "✅ Да, удалить",
            callback_data=f"profile_delete_confirm:{sim_id}",
        ),
        InlineKeyboardButton(
            "❌ Отмена",
            callback_data="profile_back",
        ),
    ]])

# /profile — главная страница

async def profile_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    engine,
) -> None:

    # ✅ Определяем reply в зависимости от типа update
    if update.message:
        reply_text  = update.message.reply_text
        telegram_id = update.message.from_user.id
    else:
        query = update.callback_query
        await query.answer()
        reply_text  = query.message.reply_text
        telegram_id = query.from_user.id

    try:
        summary     = get_profile_summary(engine, telegram_id)
        simulations = get_user_simulations(engine, telegram_id)
    except Exception as e:
        logger.error(f"[profile] failed for user={telegram_id}: {e}")
        await reply_text(
            "❌ Не удалось загрузить профиль. Попробуй позже.",
            parse_mode="HTML",
        )
        return

    if not simulations:
        await reply_text(
            "👤 <b>Your Profile</b>\n\n"
            "📭 У тебя ещё нет симуляций.\n\n"
            "Запусти первую: /simulate",
            parse_mode="HTML",
        )
        return

    await reply_text(
        format_profile_summary(summary),
        parse_mode="HTML",
    )

    await reply_text(
        format_simulation_list(simulations),
        parse_mode="HTML",
        reply_markup=_simulations_keyboard(simulations),
    )

# Детализация одной симуляции 

async def profile_detail(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    engine,
) -> None:

    query       = update.callback_query
    telegram_id = update.effective_user.id
    sim_id      = int(query.data.split(":")[1])

    await query.answer()

    try:
        sim = get_user_simulation_detail(engine, sim_id, telegram_id)
    except Exception as e:
        logger.error(f"[profile] detail failed sim_id={sim_id}: {e}")
        await query.answer("❌ Не удалось загрузить симуляцию", show_alert=True)
        return

    if not sim:
        await query.answer("❌ Симуляция не найдена", show_alert=True)
        return

    # Сохраняем sim_id для кнопки Назад
    context.user_data["viewed_sim_id"] = sim_id

    summary_dict = {
        "symbol":          sim["symbol"],
        "side":            sim["side"],
        "notional_usdt":   float(sim["notional_usdt"]),
        "date_from":       sim["date_from"],
        "date_to":         sim["date_to"],
        "days":            sim["days"],
        "intervals_count": sim["intervals_count"],
        "avg_entry_price": None,
        "funding_pnl":     float(sim["funding_pnl"]),
        "fees":            float(sim["fees"]),
        "total_pnl":       float(sim["total_pnl"]),
        "total_pnl_pct":   float(sim["total_pnl_pct"]),
    }

    await query.message.reply_text(
        format_simulation_summary(summary_dict),
        parse_mode="HTML",
        reply_markup=_detail_keyboard(sim_id), 
        )


# Кнопка Назад к профилю

async def profile_back(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    engine,
) -> None:

    query       = update.callback_query
    telegram_id = update.effective_user.id

    await query.answer()

    try:
        summary     = get_profile_summary(engine, telegram_id)
        simulations = get_user_simulations(engine, telegram_id)
    except Exception as e:
        logger.error(f"[profile] back failed for user={telegram_id}: {e}")
        await query.answer("❌ Ошибка загрузки", show_alert=True)
        return

    await query.message.reply_text(
        format_profile_summary(summary),
        parse_mode="HTML",
    )

    await query.message.reply_text(
        format_simulation_list(simulations),
        parse_mode="HTML",
        reply_markup=_simulations_keyboard(simulations),
    )

# Кнопка Обновить

async def profile_refresh(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    engine,
) -> None:

    query       = update.callback_query
    telegram_id = update.effective_user.id

    await query.answer("🔄 Обновляю...")

    try:
        summary     = get_profile_summary(engine, telegram_id)
        simulations = get_user_simulations(engine, telegram_id)
    except Exception as e:
        logger.error(f"[profile] refresh failed for user={telegram_id}: {e}")
        await query.answer("❌ Ошибка обновления", show_alert=True)
        return

    try:
        await query.edit_message_text(
            format_simulation_list(simulations),
            parse_mode="HTML",
            reply_markup=_simulations_keyboard(simulations),
        )
    except Exception:
        pass

# Регистрация хендлеров в bot.py

def register_profile_handlers(app, engine) -> None:

    app.add_handler(CommandHandler(
        "profile",
        lambda u, c: profile_command(u, c, engine),
    ))
    app.add_handler(CallbackQueryHandler(
        lambda u, c: profile_detail(u, c, engine),
        pattern="^profile_detail:",
    ))
    app.add_handler(CallbackQueryHandler(
        lambda u, c: profile_back(u, c, engine),
        pattern="^profile_back$",
    ))
    app.add_handler(CallbackQueryHandler(
        lambda u, c: profile_refresh(u, c, engine),
        pattern="^profile_refresh$",
    ))

async def profile_delete(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:

    query  = update.callback_query
    sim_id = int(query.data.split(":")[1])
    await query.answer()

    await query.message.reply_text(
        "🗑 <b>Удалить симуляцию?</b>\n\n"
        "Это действие нельзя отменить.",
        parse_mode="HTML",
        reply_markup=_confirm_delete_keyboard(sim_id),
    )

async def profile_delete_confirm(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    engine,
) -> None:

    from app.bots.funding_bot.queries.simulation import delete_simulation

    query       = update.callback_query
    telegram_id = update.effective_user.id
    sim_id      = int(query.data.split(":")[1])

    await query.answer()

    try:
        deleted = delete_simulation(engine, sim_id, telegram_id)
    except Exception as e:
        logger.error(f"[profile] delete failed sim_id={sim_id}: {e}")
        await query.answer("❌ Ошибка при удалении", show_alert=True)
        return

    if not deleted:
        await query.answer("❌ Симуляция не найдена", show_alert=True)
        return

    await query.message.reply_text(
        "✅ Симуляция удалена.",
        parse_mode="HTML",
    )

    # Показываем обновлённый профиль
    try:
        from app.bots.funding_bot.queries.simulation import (
            get_profile_summary,
            get_user_simulations,
        )
        summary     = get_profile_summary(engine, telegram_id)
        simulations = get_user_simulations(engine, telegram_id)
    except Exception as e:
        logger.error(f"[profile] reload after delete failed: {e}")
        return

    if not simulations:
        await query.message.reply_text(
            "👤 <b>Your Profile</b>\n\n"
            "📭 Симуляций больше нет.\n\nЗапусти новую: /simulate",
            parse_mode="HTML",
            reply_markup=with_menu_button([])
        )
        return

    await query.message.reply_text(
        format_profile_summary(summary),
        parse_mode="HTML",
    )
    await query.message.reply_text(
        format_simulation_list(simulations),
        parse_mode="HTML",
        reply_markup=_simulations_keyboard(simulations),
    )

    logger.info(f"[profile] deleted sim_id={sim_id} for user={telegram_id}")


def register_profile_handlers(app, engine) -> None:
    app.add_handler(CommandHandler(
        "profile",
        lambda u, c: profile_command(u, c, engine),
    ))
    app.add_handler(CallbackQueryHandler(
        lambda u, c: profile_detail(u, c, engine),
        pattern="^profile_detail:",
    ))
    app.add_handler(CallbackQueryHandler(
        lambda u, c: profile_back(u, c, engine),
        pattern="^profile_back$",
    ))
    app.add_handler(CallbackQueryHandler(
        lambda u, c: profile_refresh(u, c, engine),
        pattern="^profile_refresh$",
    ))
    # ✅ Новые
    app.add_handler(CallbackQueryHandler(
        profile_delete,
        pattern="^profile_delete:",
    ))
    app.add_handler(CallbackQueryHandler(
        lambda u, c: profile_delete_confirm(u, c, engine),
        pattern="^profile_delete_confirm:",
    ))
    