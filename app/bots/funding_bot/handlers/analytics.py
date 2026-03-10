import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from app.bots.funding_bot.utils import with_menu_button
from app.bots.funding_bot.queries.funding_stats import (
    get_funding_history_for_symbol,
)
from app.bots.funding_bot.queries.basis_stats import (
    get_basis_history,
    get_basis_summary,
)
from app.bots.funding_bot.formatters.analytics_fmt import (
    plot_funding_history,
    plot_basis_history,
)
from app.bots.funding_bot.formatters.funding_fmt import (
    format_funding_history,
)


from config import SYMBOLS

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Клавиатура выбора символа
# ---------------------------------------------------------------------------

def _symbol_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(
            s.upper(),
            callback_data=f"analytics_sym:{s.upper()}",
        )
        for s in SYMBOLS
    ]
    rows = [buttons[i:i+3] for i in range(0, len(buttons), 3)]
    return InlineKeyboardMarkup(rows)


# ---------------------------------------------------------------------------
# /stats — показываем выбор символа
# ---------------------------------------------------------------------------

async def analytics_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:

    if update.message:
        reply_text = update.message.reply_text
    else:
        query = update.callback_query
        await query.answer()
        reply_text = query.message.reply_text

    await reply_text(
        "📈 <b>Analytics</b>\n\n"
        "Выбери символ для анализа:",
        parse_mode="HTML",
        reply_markup=_symbol_keyboard(),
        
    )


# ---------------------------------------------------------------------------
# Нажатие на символ — отправляем графики
# ---------------------------------------------------------------------------

async def analytics_symbol_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    engine,
) -> None:

    query  = update.callback_query
    symbol = query.data.split(":")[1]
    await query.answer()

    # Убираем клавиатуру
    await query.edit_message_reply_markup(reply_markup=None)

    await query.message.reply_text(
        f"⏳ Загружаю аналитику для <b>{symbol}</b>...",
        parse_mode="HTML",
    )

    try:
        funding_data = get_funding_history_for_symbol(engine, symbol, days=30)
        basis_data   = get_basis_history(engine, symbol, hours=24 * 7)
        basis_summary = get_basis_summary(engine, symbol, days=7)
    except Exception as e:
        logger.error(f"[analytics] failed for {symbol}: {e}")
        await query.message.reply_text(
            "❌ Ошибка при загрузке данных.",
            parse_mode="HTML",
            reply_markup=with_menu_button([])
        )
        return

    if not funding_data and not basis_data:
        await query.message.reply_text(
            f"📭 Нет данных по <b>{symbol}</b>.\n\n"
            "Данные накапливаются — попробуй позже.",
            parse_mode="HTML",
            reply_markup=with_menu_button([])
        )
        return

    # Funding history — текст + график
    if funding_data:
        await query.message.reply_text(
            format_funding_history(funding_data, symbol),
            parse_mode="HTML",
        )
        buf = plot_funding_history(funding_data, symbol)
        await query.message.reply_photo(photo=buf)

    # Basis history — только график
    if basis_data:
        buf = plot_basis_history(basis_data, symbol)
        await query.message.reply_photo(photo=buf)

    # Basis summary — текст
    if basis_summary:
        await query.message.reply_text(
            _format_basis_summary(basis_summary, symbol),
            parse_mode="HTML",
            reply_markup=with_menu_button([]),
        )

    logger.info(f"[analytics] sent charts for {symbol}")


# ---------------------------------------------------------------------------
# Форматтер basis summary — простой, прямо здесь
# ---------------------------------------------------------------------------

def _format_basis_summary(data, symbol: str) -> str:
    avg_basis  = float(data["avg_basis_pct"]   or 0)
    std_basis  = float(data["std_basis_pct"]   or 0)
    min_basis  = float(data["min_basis_abs"]   or 0)
    max_basis  = float(data["max_basis_abs"]   or 0)
    spot_spread = float(data["avg_spot_spread"] or 0)
    fut_spread  = float(data["avg_fut_spread"]  or 0)

    return (
        f"📊 <b>Basis Summary — {symbol} (7d)</b>\n"
        "\n"
        f"Avg basis:     <code>{avg_basis:+.4f}%</code>\n"
        f"Std basis:     <code>{std_basis:.4f}%</code>\n"
        f"Min basis:     <code>{min_basis:.4f}%</code>\n"
        f"Max basis:     <code>{max_basis:.4f}%</code>\n"
        "\n"
        f"Spot spread:   <code>{spot_spread:.4f}%</code>\n"
        f"Fut spread:    <code>{fut_spread:.4f}%</code>\n"
    )


# ---------------------------------------------------------------------------
# Регистрация
# ---------------------------------------------------------------------------

def register_analytics_handlers(app, engine) -> None:
    app.add_handler(CommandHandler(
        "stats",
        lambda u, c: analytics_command(u, c),
    ))
    app.add_handler(CallbackQueryHandler(
        lambda u, c: analytics_symbol_callback(u, c, engine),
        pattern="^analytics_sym:",
    ))