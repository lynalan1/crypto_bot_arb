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

from app.bots.funding_bot.utils import with_menu_button
from config import SYMBOLS

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Состояния
# ---------------------------------------------------------------------------

CHOOSE_SYMBOL, ENTER_SYMBOL = range(2)

TOP_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT",
    "ARBUSDT", "OPUSDT",  "AVAXUSDT", "LINKUSDT",
]

# ---------------------------------------------------------------------------
# Вспомогательные функции
# ---------------------------------------------------------------------------

def _next_funding_countdown() -> str:
    """Binance выплачивает funding в 00:00 / 08:00 / 16:00 UTC."""
    now       = datetime.now(timezone.utc)
    next_hour = ((now.hour // 8) + 1) * 8 % 24
    next_dt   = now.replace(hour=next_hour, minute=0, second=0, microsecond=0)

    if next_dt <= now:
        next_dt += timedelta(days=1)

    delta   = next_dt - now
    hours   = delta.seconds // 3600
    minutes = (delta.seconds % 3600) // 60
    seconds = delta.seconds % 60

    return (
        f"⏰ <b>Следующая выплата через:</b> "
        f"<code>{hours:02d}:{minutes:02d}:{seconds:02d}</code> "
        f"<i>(в {next_dt.strftime('%H:%M')} UTC)</i>"
    )


def _symbol_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(s, callback_data=f"pos_sym:{s}")
        for s in TOP_SYMBOLS
    ]
    rows = [buttons[i:i+4] for i in range(0, len(buttons), 4)]
    rows.append([
        InlineKeyboardButton("✏️ Ввести вручную", callback_data="pos_manual"),
    ])
    rows.append([
        InlineKeyboardButton("🏠 Главное меню", callback_data="go_menu"),
    ])
    return InlineKeyboardMarkup(rows)


def _detail_keyboard(symbol: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔄 Обновить",     callback_data=f"pos_sym:{symbol}"),
            InlineKeyboardButton("◀️ К списку",     callback_data="pos_back"),
        ],
        [
            InlineKeyboardButton("🧮 Симулировать", callback_data="menu_simulate"),
            InlineKeyboardButton("🏠 Меню",         callback_data="go_menu"),
        ],
    ])

# ---------------------------------------------------------------------------
# Шаг 1 — /positions
# ---------------------------------------------------------------------------

async def positions_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    engine=None,
) -> int:

    if update.message:
        reply = update.message.reply_text
    else:
        query = update.callback_query
        await query.answer()
        reply = query.message.reply_text

    await reply(
        f"📊 <b>Funding по символу</b>\n\n"
        f"{_next_funding_countdown()}\n\n"
        "Выбери символ или введи вручную:",
        parse_mode="HTML",
        reply_markup=_symbol_keyboard(),
    )
    return CHOOSE_SYMBOL

# ---------------------------------------------------------------------------
# Шаг 2а — нажали кнопку символа
# ---------------------------------------------------------------------------

async def positions_symbol_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    engine,
) -> int:

    query  = update.callback_query
    symbol = query.data.split(":")[1].upper()
    await query.answer()

    await _send_symbol_detail(query.message.reply_text, symbol, engine)
    return ConversationHandler.END

# ---------------------------------------------------------------------------
# Шаг 2б — нажали "ввести вручную"
# ---------------------------------------------------------------------------

async def positions_ask_manual(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:

    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        "✏️ <b>Введи символ</b>\n\n"
        "Например: <code>DOGEUSDT</code>, <code>dogeusdt</code>\n"
        "<i>Регистр не важен</i>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("◀️ Назад",        callback_data="pos_back"),
            InlineKeyboardButton("🏠 Главное меню", callback_data="go_menu"),
        ]]),
    )
    return ENTER_SYMBOL

# ---------------------------------------------------------------------------
# Шаг 2в — пользователь написал символ
# ---------------------------------------------------------------------------

async def positions_enter_symbol(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    engine,
) -> int:

    symbol = update.message.text.strip().upper()

    if not symbol.isalnum() or len(symbol) < 5 or len(symbol) > 12:
        await update.message.reply_text(
            "❌ Некорректный символ.\n"
            "Формат: <code>BTCUSDT</code>\n"
            "Попробуй ещё раз:",
            parse_mode="HTML",
        )
        return ENTER_SYMBOL

    await _send_symbol_detail(update.message.reply_text, symbol, engine)
    return ConversationHandler.END

# ---------------------------------------------------------------------------
# Назад к списку
# ---------------------------------------------------------------------------

async def positions_back(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:

    query = update.callback_query
    await query.answer()

    await query.message.reply_text(
        f"📊 <b>Funding по символу</b>\n\n"
        f"{_next_funding_countdown()}\n\n"
        "Выбери символ или введи вручную:",
        parse_mode="HTML",
        reply_markup=_symbol_keyboard(),
    )
    return CHOOSE_SYMBOL

# ---------------------------------------------------------------------------
# Основная логика — загрузка и отправка данных по символу
# ---------------------------------------------------------------------------

async def _send_symbol_detail(reply_fn, symbol: str, engine) -> None:

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
                    AVG(funding_rate)                               AS avg_rate_30d,
                    SUM(CASE WHEN funding_rate > 0 THEN 1 ELSE 0 END)
                        * 1.0 / NULLIF(COUNT(*), 0)                AS positive_ratio,
                    MAX(funding_rate)                               AS max_rate,
                    MIN(funding_rate)                               AS min_rate,
                    COUNT(*)                                        AS total_intervals
                FROM funding_events
                WHERE UPPER(symbol) = :symbol
                AND   funding_time >= now() - (30 * interval '1 day')
            """), {"symbol": symbol}).mappings().first()

    except Exception as e:
        logger.error(f"[positions] detail failed {symbol}: {e}")
        await reply_fn("❌ Ошибка при загрузке данных.", parse_mode="HTML")
        return

    if not last:
        await reply_fn(
            f"📭 Нет данных по <b>{symbol}</b>.\n\n"
            "Проверь правильность написания.",
            parse_mode="HTML",
            reply_markup=_symbol_keyboard(),
        )
        return

    current_rate = float(last["funding_rate"])
    avg_rate     = float(stats["avg_rate_30d"]   or 0)
    pos_ratio    = float(stats["positive_ratio"] or 0)
    max_rate     = float(stats["max_rate"]       or 0)
    min_rate     = float(stats["min_rate"]       or 0)
    intervals    = stats["total_intervals"]
    last_time    = last["funding_time"].strftime("%d.%m.%Y %H:%M UTC")

    rate_sign = "🟢" if current_rate >= 0 else "🔴"
    avg_sign  = "🟢" if avg_rate     >= 0 else "🔴"

    # Грубая аннуализация: 3 выплаты/день × 365
    annual_yield = avg_rate * 3 * 365 * 100

    msg = (
        f"📊 <b>Funding — {symbol}</b>\n"
        "\n"
        f"{_next_funding_countdown()}\n"
        "\n"
        f"{rate_sign} <b>Текущий rate:</b>  <code>{current_rate:+.4%}</code>\n"
        f"   <i>последняя выплата: {last_time}</i>\n"
        "\n"
        f"📅 <b>Статистика за 30 дней:</b>\n"
        f"{avg_sign} Avg rate:       <code>{avg_rate:+.4%}</code>\n"
        f"   Positive:      <code>{pos_ratio:.1%}</code> интервалов\n"
        f"   Max rate:      <code>{max_rate:+.4%}</code>\n"
        f"   Min rate:      <code>{min_rate:+.4%}</code>\n"
        f"   Интервалов:    <code>{intervals}</code>\n"
        "\n"
        f"📈 <b>~{annual_yield:.1f}% годовых</b> "
        f"<i>(грубо, без fees)</i>\n"
    )

    await reply_fn(
        msg,
        parse_mode="HTML",
        reply_markup=_detail_keyboard(symbol),
    )

    logger.info(f"[positions] sent detail for {symbol}")

# ---------------------------------------------------------------------------
# Регистрация
# ---------------------------------------------------------------------------

def build_positions_handler(engine) -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            CommandHandler(
                "positions",
                lambda u, c: positions_command(u, c, engine),
            ),
            CallbackQueryHandler(
                lambda u, c: positions_command(u, c, engine),
                pattern="^menu_positions$",
            ),
        ],
        states={
            CHOOSE_SYMBOL: [
                CallbackQueryHandler(
                    lambda u, c: positions_symbol_callback(u, c, engine),
                    pattern="^pos_sym:",
                ),
                CallbackQueryHandler(
                    positions_ask_manual,
                    pattern="^pos_manual$",
                ),
                CallbackQueryHandler(
                    lambda u, c: positions_back(u, c),
                    pattern="^pos_back$",
                ),
            ],
            ENTER_SYMBOL: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    lambda u, c: positions_enter_symbol(u, c, engine),
                ),
                CallbackQueryHandler(
                    lambda u, c: positions_back(u, c),
                    pattern="^pos_back$",
                ),
            ],
        },
        fallbacks=[],
        per_user=True,
        per_chat=True,
    )


def register_positions_handlers(app, engine) -> None:
    app.add_handler(build_positions_handler(engine))