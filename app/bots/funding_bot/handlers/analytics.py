import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    filters,
)

from app.bots.funding_bot.queries.funding_stats import get_funding_history_for_symbol
from app.bots.funding_bot.queries.basis_stats import get_basis_history, get_basis_summary
from app.bots.funding_bot.formatters.analytics_fmt import plot_funding_history, plot_basis_history
from app.bots.funding_bot.formatters.funding_fmt import format_funding_history
from app.bots.funding_bot.utils import with_menu_button, get_lang
from app.bots.funding_bot.i18n import t

logger = logging.getLogger(__name__)

CHOOSE_SYMBOL, ENTER_SYMBOL = range(2)

TOP_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT",
    "ARBUSDT", "OPUSDT", "AVAXUSDT", "LINKUSDT",
]

def _symbol_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    buttons = [InlineKeyboardButton(s, callback_data=f"analytics_sym:{s}") for s in TOP_SYMBOLS]
    rows = [buttons[i:i+4] for i in range(0, len(buttons), 4)]
    rows.append([InlineKeyboardButton(t(lang, "btn_manual_input"), callback_data="analytics_manual")])
    rows.append([InlineKeyboardButton(t(lang, "btn_menu"), callback_data="go_menu")])
    return InlineKeyboardMarkup(rows)

async def analytics_command(update: Update, context: ContextTypes.DEFAULT_TYPE, engine=None) -> int:
    lang = get_lang(context, engine, update.effective_user.id) if engine else context.user_data.get("lang", "ru")
    reply = update.message.reply_text if update.message else update.callback_query.message.reply_text
    if not update.message:
        await update.callback_query.answer()
    await reply(t(lang, "analytics_title"), parse_mode="HTML", reply_markup=_symbol_keyboard(lang))
    return CHOOSE_SYMBOL

async def analytics_symbol_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, engine) -> int:
    query  = update.callback_query
    symbol = query.data.split(":")[1].upper()
    lang   = get_lang(context, engine, update.effective_user.id)
    await query.answer()
    await query.edit_message_reply_markup(reply_markup=None)
    await _send_analytics(query.message.reply_text, query.message.reply_photo, symbol, engine, lang)
    return ConversationHandler.END

async def analytics_ask_manual(update: Update, context: ContextTypes.DEFAULT_TYPE, engine=None) -> int:
    query = update.callback_query
    await query.answer()
    lang = context.user_data.get("lang", "ru")
    await query.edit_message_text(
        t(lang, "manual_prompt"),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton(t(lang, "btn_back"), callback_data="analytics_back"),
            InlineKeyboardButton(t(lang, "btn_menu"), callback_data="go_menu"),
        ]]),
    )
    return ENTER_SYMBOL

async def analytics_enter_symbol(update: Update, context: ContextTypes.DEFAULT_TYPE, engine) -> int:
    symbol = update.message.text.strip().upper()
    lang   = context.user_data.get("lang", "ru")
    if not symbol.isalnum() or len(symbol) < 5 or len(symbol) > 12:
        await update.message.reply_text(t(lang, "invalid_symbol"), parse_mode="HTML")
        return ENTER_SYMBOL
    await _send_analytics(update.message.reply_text, update.message.reply_photo, symbol, engine, lang)
    return ConversationHandler.END

async def analytics_back(update: Update, context: ContextTypes.DEFAULT_TYPE, engine=None) -> int:
    query = update.callback_query
    await query.answer()
    lang = context.user_data.get("lang", "ru")
    await query.message.reply_text(t(lang, "analytics_title"), parse_mode="HTML", reply_markup=_symbol_keyboard(lang))
    return CHOOSE_SYMBOL

async def _send_analytics(reply_text, reply_photo, symbol: str, engine, lang: str = "ru") -> None:
    await reply_text(t(lang, "analytics_loading", symbol=symbol), parse_mode="HTML")
    try:
        funding_data  = get_funding_history_for_symbol(engine, symbol, days=30)
        basis_data    = get_basis_history(engine, symbol, hours=24 * 7)
        basis_summary = get_basis_summary(engine, symbol, days=7)
    except Exception as e:
        logger.error(f"[analytics] failed for {symbol}: {e}")
        await reply_text(t(lang, "analytics_error"), parse_mode="HTML")
        return

    if not funding_data and not basis_data:
        await reply_text(t(lang, "analytics_no_data", symbol=symbol), parse_mode="HTML", reply_markup=with_menu_button([], lang))
        return

    if funding_data:
        await reply_text(format_funding_history(funding_data, symbol), parse_mode="HTML")
        buf = plot_funding_history(funding_data, symbol)
        await reply_photo(photo=buf)

    if basis_data:
        buf = plot_basis_history(basis_data, symbol)
        await reply_photo(photo=buf)

    if basis_summary:
        await reply_text(_format_basis_explained(basis_summary, symbol, lang), parse_mode="HTML", reply_markup=with_menu_button([], lang))

    logger.info(f"[analytics] sent for {symbol}")

def _format_basis_explained(data, symbol: str, lang: str = "ru") -> str:
    avg_basis   = float(data["avg_basis_pct"] or 0)
    std_basis   = float(data["std_basis_pct"] or 0)
    min_basis   = float(data["min_basis_abs"] or 0)
    max_basis   = float(data["max_basis_abs"] or 0)
    spot_spread = float(data["avg_spot_spread"] or 0)
    fut_spread  = float(data["avg_fut_spread"] or 0)

    spot_spread_pct = spot_spread * 100
    fut_spread_pct  = fut_spread * 100
    avg_sign = "🟢" if avg_basis >= 0 else "🔴"

    if lang == "en":
        # English verdicts
        if abs(avg_basis) < 0.0005: basis_verdict = "📊 Basis is near zero — futures trading close to spot."
        elif avg_basis > 0: basis_verdict = "📈 Futures trading <b>above</b> spot — market in contango."
        else: basis_verdict = "📉 Futures trading <b>below</b> spot — market in backwardation."
        std_verdict = "🟢 Basis stable" if std_basis < 0.001 else "🟡 Basis moderately volatile" if std_basis < 0.005 else "🔴 Basis highly volatile"
        spread_verdict = "🟢 Minimal spreads" if spot_spread_pct < 0.001 and fut_spread_pct < 0.001 else "🟡 Small spreads" if spot_spread_pct < 0.01 else "🔴 High spreads"
        return f"📊 <b>Basis Summary — {symbol} (7d)</b>\n\n{avg_sign} <b>Avg basis:</b>  <code>{avg_basis:+.4%}</code>\n{basis_verdict}\n📏 <b>Std basis:</b> <code>{std_basis:.4%}</code>\n{std_verdict}\n📉 <b>Min basis:</b> <code>{min_basis:+.4%}</code>\n📈 <b>Max basis:</b> <code>{max_basis:+.4%}</code>\n💹 <b>Spot spread:</b> <code>{spot_spread_pct:.6f}%</code>\n💹 <b>Fut spread:</b> <code>{fut_spread_pct:.6f}%</code>\n{spread_verdict}"

    # Russian verdicts
    if abs(avg_basis) < 0.0005: basis_verdict = "📊 Basis близок к нулю — фьючерс торгуется почти по цене спота."
    elif avg_basis > 0: basis_verdict = "📈 Фьючерс торгуется <b>дороже</b> спота — рынок в контанго."
    else: basis_verdict = "📉 Фьючерс торгуется <b>дешевле</b> спота — рынок в бэквордации."
    std_verdict = "🟢 Basis стабилен" if std_basis < 0.001 else "🟡 Basis умеренно волатилен" if std_basis < 0.005 else "🔴 Basis сильно волатилен"
    if spot_spread_pct < 0.001 and fut_spread_pct < 0.001: spread_verdict = "🟢 Спреды минимальны — ликвидность отличная."
    elif spot_spread_pct < 0.01: spread_verdict = "🟡 Спреды небольшие — ликвидность хорошая."
    else: spread_verdict = "🔴 Высокие спреды — учитывай при расчёте реальных издержек."

    return f"📊 <b>Basis Summary — {symbol} (7d)</b>\n\n{avg_sign} <b>Avg basis:</b>  <code>{avg_basis:+.4%}</code>\n{basis_verdict}\n📏 <b>Std basis:</b> <code>{std_basis:.4%}</code>\n{std_verdict}\n📉 <b>Min basis:</b> <code>{min_basis:+.4%}</code>\n📈 <b>Max basis:</b> <code>{max_basis:+.4%}</code>\n💹 <b>Spot spread:</b> <code>{spot_spread_pct:.6f}%</code>\n💹 <b>Fut spread:</b> <code>{fut_spread_pct:.6f}%</code>\n{spread_verdict}"

def build_analytics_handler(engine) -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            CommandHandler("stats", lambda u, c: analytics_command(u, c, engine)),
            CallbackQueryHandler(lambda u, c: analytics_command(u, c, engine), pattern="^menu_analytics$"),
        ],
        states={
            CHOOSE_SYMBOL: [
                CallbackQueryHandler(lambda u, c: analytics_symbol_callback(u, c, engine), pattern="^analytics_sym:"),
                CallbackQueryHandler(lambda u, c: analytics_ask_manual(u, c, engine), pattern="^analytics_manual$"),
                CallbackQueryHandler(lambda u, c: analytics_back(u, c, engine), pattern="^analytics_back$"),
            ],
            ENTER_SYMBOL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, lambda u, c: analytics_enter_symbol(u, c, engine)),
                CallbackQueryHandler(lambda u, c: analytics_back(u, c, engine), pattern="^analytics_back$"),
            ],
        },
        fallbacks=[],
        per_user=True,
        per_chat=True,
    )

def register_analytics_handlers(app, engine) -> None:
    app.add_handler(build_analytics_handler(engine))

    