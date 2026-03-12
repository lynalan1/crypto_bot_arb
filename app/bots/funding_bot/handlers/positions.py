import logging
from datetime import datetime, timezone, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    filters,
)
from sqlalchemy import text

from app.bots.funding_bot.i18n import t
from app.bots.funding_bot.utils import get_lang

logger = logging.getLogger(__name__)

CHOOSE_SYMBOL, ENTER_SYMBOL = range(2)

TOP_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT",
    "ARBUSDT", "OPUSDT", "AVAXUSDT", "LINKUSDT",
]

def _next_funding_countdown(lang: str = "ru") -> str:
    now       = datetime.now(timezone.utc)
    next_hour = ((now.hour // 8) + 1) * 8 % 24
    next_dt   = now.replace(hour=next_hour, minute=0, second=0, microsecond=0)
    if next_dt <= now:
        next_dt += timedelta(days=1)
    delta   = next_dt - now
    hours   = delta.seconds // 3600
    minutes = (delta.seconds % 3600) // 60
    seconds = delta.seconds % 60
    time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    hour_str = next_dt.strftime('%H:%M')
    return t(lang, "next_payment", time=time_str, hour=hour_str)

def _symbol_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    buttons = [InlineKeyboardButton(s, callback_data=f"pos_sym:{s}") for s in TOP_SYMBOLS]
    rows = [buttons[i:i+4] for i in range(0, len(buttons), 4)]
    rows.append([InlineKeyboardButton(t(lang, "btn_manual_input"), callback_data="pos_manual")])
    rows.append([InlineKeyboardButton(t(lang, "btn_menu"), callback_data="go_menu")])
    return InlineKeyboardMarkup(rows)

def _detail_keyboard(symbol: str, lang: str = "ru") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(t(lang, "btn_refresh"), callback_data=f"pos_sym:{symbol}"),
            InlineKeyboardButton(t(lang, "btn_to_list"), callback_data="pos_back"),
        ],
        [
            InlineKeyboardButton(t(lang, "btn_simulate_this"), callback_data="menu_simulate"),
            InlineKeyboardButton(t(lang, "btn_menu"), callback_data="go_menu"),
        ],
    ])

async def positions_command(update: Update, context: ContextTypes.DEFAULT_TYPE, engine=None) -> int:
    lang = get_lang(context, engine, update.effective_user.id)
    if update.message:
        reply = update.message.reply_text
    else:
        query = update.callback_query
        await query.answer()
        reply = query.message.reply_text
    await reply(
        f"{t(lang, 'positions_title')}\n\n"
        f"{_next_funding_countdown(lang)}\n\n"
        f"{t(lang, 'positions_choose')}",
        parse_mode="HTML",
        reply_markup=_symbol_keyboard(lang),
    )
    return CHOOSE_SYMBOL

async def positions_symbol_callback(update, context, engine):
    query  = update.callback_query
    symbol = query.data.split(":")[1].upper()
    lang   = get_lang(context, engine, update.effective_user.id)
    await query.answer()
    await _send_symbol_detail(query.message.reply_text, symbol, engine, lang)
    return CHOOSE_SYMBOL 

async def positions_ask_manual(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    lang  = context.user_data.get("lang", "ru")
    await query.edit_message_text(
        t(lang, "manual_prompt"),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton(t(lang, "btn_back"), callback_data="pos_back"),
            InlineKeyboardButton(t(lang, "btn_menu"), callback_data="go_menu"),
        ]]),
    )
    return ENTER_SYMBOL

async def positions_enter_symbol(update: Update, context: ContextTypes.DEFAULT_TYPE, engine) -> int:
    symbol = update.message.text.strip().upper()
    lang   = context.user_data.get("lang", "ru")
    if not symbol.isalnum() or len(symbol) < 5 or len(symbol) > 12:
        await update.message.reply_text(t(lang, "invalid_symbol"), parse_mode="HTML")
        return ENTER_SYMBOL
    await _send_symbol_detail(update.message.reply_text, symbol, engine, lang)
    return CHOOSE_SYMBOL

async def positions_back(update: Update, context: ContextTypes.DEFAULT_TYPE, engine=None) -> int:
    query = update.callback_query
    await query.answer()
    lang  = context.user_data.get("lang", "ru")
    await query.message.reply_text(
        f"{t(lang, 'positions_title')}\n\n"
        f"{_next_funding_countdown(lang)}\n\n"
        f"{t(lang, 'positions_choose')}",
        parse_mode="HTML",
        reply_markup=_symbol_keyboard(lang),
    )
    return CHOOSE_SYMBOL

async def _send_symbol_detail(reply_fn, symbol: str, engine, lang: str = "ru") -> None:
    try:
        with engine.connect() as conn:
            last = conn.execute(text("""
                SELECT funding_rate, funding_time
                FROM funding_events
                WHERE UPPER(symbol) = :symbol
                ORDER BY funding_time DESC
                LIMIT 1
            """), {"symbol": symbol}).mappings().first()
            stats = conn.execute(text("""
                SELECT
                    AVG(funding_rate) AS avg_rate_30d,
                    SUM(CASE WHEN funding_rate > 0 THEN 1 ELSE 0 END) * 1.0 / NULLIF(COUNT(*), 0) AS positive_ratio,
                    MAX(funding_rate) AS max_rate,
                    MIN(funding_rate) AS min_rate,
                    COUNT(*) AS total_intervals
                FROM funding_events
                WHERE UPPER(symbol) = :symbol
                AND funding_time >= now() - (30 * interval '1 day')
            """), {"symbol": symbol}).mappings().first()
    except Exception as e:
        logger.error(f"[positions] detail failed {symbol}: {e}")
        await reply_fn(t(lang, "error"), parse_mode="HTML")
        return

    if not last:
        await reply_fn(t(lang, "no_symbol_data", symbol=symbol), parse_mode="HTML", reply_markup=_symbol_keyboard(lang))
        return

    current_rate = float(last["funding_rate"])
    avg_rate     = float(stats["avg_rate_30d"]   or 0)
    pos_ratio    = float(stats["positive_ratio"] or 0)
    max_rate     = float(stats["max_rate"]       or 0)
    min_rate     = float(stats["min_rate"]       or 0)
    intervals    = stats["total_intervals"]
    last_time    = last["funding_time"].strftime("%d.%m.%Y %H:%M UTC")
    rate_sign = "🟢" if current_rate >= 0 else "🔴"
    avg_sign  = "🟢" if avg_rate >= 0 else "🔴"
    annual_yield = avg_rate * 3 * 365 * 100

    msg = t(lang, "positions_detail",
        symbol=symbol,
        countdown=_next_funding_countdown(lang),
        rate_sign=rate_sign,
        current_rate=current_rate,
        last_time=last_time,
        avg_sign=avg_sign,
        avg_rate=avg_rate,
        pos_ratio=pos_ratio,
        max_rate=max_rate,
        min_rate=min_rate,
        intervals=intervals,
        annual=annual_yield,
    )

    await reply_fn(msg, parse_mode="HTML", reply_markup=_detail_keyboard(symbol, lang))
    logger.info(f"[positions] sent detail for {symbol}")

def build_positions_handler(engine) -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            CommandHandler("positions", lambda u, c: positions_command(u, c, engine)),
            CallbackQueryHandler(lambda u, c: positions_command(u, c, engine), pattern="^menu_positions$"),
        ],
        states={
            CHOOSE_SYMBOL: [
                CallbackQueryHandler(lambda u, c: positions_symbol_callback(u, c, engine), pattern="^pos_sym:"),
                CallbackQueryHandler(positions_ask_manual, pattern="^pos_manual$"),
                CallbackQueryHandler(lambda u, c: positions_back(u, c, engine), pattern="^pos_back$"),
            ],
            ENTER_SYMBOL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, lambda u, c: positions_enter_symbol(u, c, engine)),
                CallbackQueryHandler(lambda u, c: positions_back(u, c, engine), pattern="^pos_back$"),
            ],
        },
        fallbacks=[],
        per_user=True,
        per_chat=True,
    )

def register_positions_handlers(app, engine) -> None:
    app.add_handler(build_positions_handler(engine))