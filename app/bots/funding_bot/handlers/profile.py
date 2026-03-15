import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler

from app.bots.funding_bot.utils import with_menu_button, get_lang
from app.bots.funding_bot.i18n import t
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

def _simulations_keyboard(simulations, lang: str = "ru") -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(
            f"{sim['symbol']} {sim['notional_usdt']:,.0f}$ {sim['total_pnl']:+.2f} {sim['days']}d",
            callback_data=f"profile_detail:{sim['id']}"
        )] for sim in simulations
    ]
    buttons.append([
        InlineKeyboardButton(t(lang, "btn_refresh"), callback_data="profile_refresh"),
        InlineKeyboardButton(t(lang, "btn_menu"),    callback_data="go_menu"),
    ])
    return InlineKeyboardMarkup(buttons)

def _detail_keyboard(sim_id: int, lang: str = "ru") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(t(lang, "btn_delete"), callback_data=f"profile_delete:{sim_id}"),
            InlineKeyboardButton(t(lang, "btn_profile_back"), callback_data="profile_back"),
        ],
    ])

def _confirm_delete_keyboard(sim_id: int, lang: str = "ru") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(t(lang, "btn_yes_delete"), callback_data=f"profile_delete_confirm:{sim_id}"),
        InlineKeyboardButton(t(lang, "btn_cancel"),     callback_data="profile_back"),
    ]])

async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE, engine) -> None:
    if update.message:
        reply_text  = update.message.reply_text
        telegram_id = update.message.from_user.id
    else:
        query = update.callback_query
        await query.answer()
        reply_text  = query.message.reply_text
        telegram_id = query.from_user.id

    lang = get_lang(context, engine, telegram_id)

    try:
        summary     = get_profile_summary(engine, telegram_id)
        simulations = get_user_simulations(engine, telegram_id)
    except Exception as e:
        logger.error(f"[profile] failed for user={telegram_id}: {e}")
        await reply_text("❌ Не удалось загрузить профиль. Попробуй позже.", parse_mode="HTML")
        return

    if not simulations:
        await reply_text(t(lang, "profile_empty"), parse_mode="HTML")
        return

    await reply_text(format_profile_summary(summary), parse_mode="HTML")
    await reply_text(format_simulation_list(simulations), parse_mode="HTML", reply_markup=_simulations_keyboard(simulations, lang))

async def profile_detail(update: Update, context: ContextTypes.DEFAULT_TYPE, engine) -> None:
    query       = update.callback_query
    telegram_id = update.effective_user.id
    sim_id      = int(query.data.split(":")[1])
    lang        = get_lang(context, engine, telegram_id)
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
        reply_markup=_detail_keyboard(sim_id, lang),
    )

async def profile_back(update: Update, context: ContextTypes.DEFAULT_TYPE, engine) -> None:
    query       = update.callback_query
    telegram_id = update.effective_user.id
    lang        = get_lang(context, engine, telegram_id)
    await query.answer()
    try:
        summary     = get_profile_summary(engine, telegram_id)
        simulations = get_user_simulations(engine, telegram_id)
    except Exception as e:
        logger.error(f"[profile] back failed for user={telegram_id}: {e}")
        await query.answer("❌ Ошибка загрузки", show_alert=True)
        return
    await query.message.reply_text(format_profile_summary(summary), parse_mode="HTML")
    await query.message.reply_text(format_simulation_list(simulations), parse_mode="HTML", reply_markup=_simulations_keyboard(simulations, lang))

async def profile_refresh(update: Update, context: ContextTypes.DEFAULT_TYPE, engine) -> None:
    query       = update.callback_query
    telegram_id = update.effective_user.id
    lang        = get_lang(context, engine, telegram_id)
    await query.answer("🔄 Обновляю..." if lang == "ru" else "🔄 Refreshing...")
    try:
        summary     = get_profile_summary(engine, telegram_id)
        simulations = get_user_simulations(engine, telegram_id)
    except Exception as e:
        logger.error(f"[profile] refresh failed for user={telegram_id}: {e}")
        await query.answer("❌ Ошибка обновления", show_alert=True)
        return
    try:
        await query.edit_message_text(format_simulation_list(simulations), parse_mode="HTML", reply_markup=_simulations_keyboard(simulations, lang))
    except Exception:
        pass

async def profile_delete(update: Update, context: ContextTypes.DEFAULT_TYPE, engine) -> None:
    query       = update.callback_query
    sim_id      = int(query.data.split(":")[1])
    telegram_id = update.effective_user.id
    lang        = get_lang(context, engine, telegram_id)
    await query.answer()
    await query.message.reply_text(t(lang, "delete_confirm"), parse_mode="HTML", reply_markup=_confirm_delete_keyboard(sim_id, lang))

async def profile_delete_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE, engine) -> None:
    from app.bots.funding_bot.queries.simulation import delete_simulation
    query       = update.callback_query
    telegram_id = update.effective_user.id
    sim_id      = int(query.data.split(":")[1])
    lang        = get_lang(context, engine, telegram_id)
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

    await query.message.reply_text(t(lang, "profile_deleted"), parse_mode="HTML")

    try:
        summary     = get_profile_summary(engine, telegram_id)
        simulations = get_user_simulations(engine, telegram_id)
    except Exception as e:
        logger.error(f"[profile] reload after delete failed: {e}")
        return

    if not simulations:
        await query.message.reply_text(t(lang, "profile_no_more"), parse_mode="HTML", reply_markup=with_menu_button([], lang))
        return

    await query.message.reply_text(format_profile_summary(summary), parse_mode="HTML")
    await query.message.reply_text(format_simulation_list(simulations), parse_mode="HTML", reply_markup=_simulations_keyboard(simulations, lang))
    logger.info(f"[profile] deleted sim_id={sim_id} for user={telegram_id}")

def register_profile_handlers(app, engine) -> None:
    app.add_handler(CommandHandler("profile", lambda u, c: profile_command(u, c, engine)))
    app.add_handler(CallbackQueryHandler(lambda u, c: profile_detail(u, c, engine), pattern="^profile_detail:"))
    app.add_handler(CallbackQueryHandler(lambda u, c: profile_back(u, c, engine), pattern="^profile_back$"))
    app.add_handler(CallbackQueryHandler(lambda u, c: profile_refresh(u, c, engine), pattern="^profile_refresh$"))
    app.add_handler(CallbackQueryHandler(lambda u, c: profile_delete(u, c, engine), pattern="^profile_delete:"))
    app.add_handler(CallbackQueryHandler(lambda u, c: profile_delete_confirm(u, c, engine), pattern="^profile_delete_confirm:"))