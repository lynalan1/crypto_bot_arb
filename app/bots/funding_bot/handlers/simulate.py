import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

from app.bots.funding_bot.queries.simulation import calculate_simulation
from app.bots.funding_bot.formatters.simulation_fmt import (
    format_simulation_summary,
    plot_simulation,
)
from app.bots.funding_bot.utils import with_menu_button

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Состояния диалога
# ---------------------------------------------------------------------------

CHOOSE_SYMBOL, CHOOSE_SIDE, ENTER_AMOUNT, CHOOSE_PERIOD, ENTER_SYMBOL = range(5)
PRESET_AMOUNTS = [100, 500, 1000, 2000, 5000]

# ---------------------------------------------------------------------------
# Топ символов для быстрого выбора
# ---------------------------------------------------------------------------

TOP_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT",
    "ARBUSDT", "OPUSDT",  "AVAXUSDT", "LINKUSDT",
]

# ---------------------------------------------------------------------------
# Клавиатуры
# ---------------------------------------------------------------------------
def _symbol_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(s, callback_data=f"sim_symbol:{s}")
        for s in TOP_SYMBOLS
    ]
    rows = [buttons[i:i+4] for i in range(0, len(buttons), 4)]
    rows.append([
        InlineKeyboardButton("✏️ Ввести вручную", callback_data="sim_symbol_manual"),
    ])
    rows.append([
        InlineKeyboardButton("🏠 Главное меню", callback_data="sim_menu"),
    ])
    return InlineKeyboardMarkup(rows)



def _side_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📈 Long spot / Short fut", callback_data="sim_side:SHORT"),
            InlineKeyboardButton("📉 Short spot / Long fut", callback_data="sim_side:LONG"),
        ],
        [
            InlineKeyboardButton("◀️ Назад",        callback_data="sim_back_to_symbol"),
            InlineKeyboardButton("🏠 Главное меню", callback_data="sim_menu"),
        ],
    ])


def _period_keyboard() -> InlineKeyboardMarkup:
    periods = [("1д", 1), ("7д", 7), ("14д", 14), ("30д", 30), ("90д", 90)]
    buttons = [
        InlineKeyboardButton(label, callback_data=f"sim_period:{days}")
        for label, days in periods
    ]
    return InlineKeyboardMarkup([
        buttons,
        [
            InlineKeyboardButton("◀️ Назад",        callback_data="sim_back_to_side"),
            InlineKeyboardButton("🏠 Главное меню", callback_data="sim_menu"),
        ],
    ])


def _result_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("💾 Сохранить в профиль", callback_data="sim_save"),
        InlineKeyboardButton("🔁 Новая симуляция",     callback_data="sim_restart"),
    ]])


def _saved_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Сохранено",        callback_data="sim_saved_noop"),
        InlineKeyboardButton("🔁 Новая симуляция",  callback_data="sim_restart"),
    ]])

# ---------------------------------------------------------------------------
# Шаг 1 — /simulate (команда или кнопка)
# ---------------------------------------------------------------------------

async def simulate_start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:

    context.user_data.clear()

    if update.message:
        reply = update.message.reply_text
    else:
        query = update.callback_query
        await query.answer()
        reply = query.message.reply_text

    await reply(
        "📊 <b>Simulation</b>\n\n"
        "Выбери символ:",
        parse_mode="HTML",
        reply_markup=_symbol_keyboard(),
    )
    return CHOOSE_SYMBOL

# ---------------------------------------------------------------------------
# Шаг 2а — выбор символа из топа
# ---------------------------------------------------------------------------

async def choose_symbol(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:

    query = update.callback_query
    await query.answer()

    symbol = query.data.split(":")[1].upper()
    context.user_data["symbol"] = symbol

    await query.edit_message_text(
        f"📊 <b>Simulation — {symbol}</b>\n\n"
        "Выбери сторону стратегии:",
        parse_mode="HTML",
        reply_markup=_side_keyboard(),
    )
    return CHOOSE_SIDE

# ---------------------------------------------------------------------------
# Шаг 2б — нажали "ввести вручную"
# ---------------------------------------------------------------------------

async def ask_manual_symbol(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:

    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        "✏️ <b>Введи символ вручную</b>\n\n"
        "Например: <code>DOGEUSDT</code>, <code>dogeusdt</code>\n"
        "<i>Регистр не важен</i>",
        parse_mode="HTML",
    )
    return ENTER_SYMBOL

# ---------------------------------------------------------------------------
# Шаг 2в — пользователь написал символ текстом
# ---------------------------------------------------------------------------

async def enter_symbol_manual(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    engine,
) -> int:

    raw    = update.message.text.strip()
    symbol = raw.upper()

    if not symbol.isalnum() or len(symbol) < 5 or len(symbol) > 12:
        await update.message.reply_text(
            "❌ Некорректный символ.\n\n"
            "Формат: <code>BTCUSDT</code>, <code>ETHUSDT</code>\n"
            "Попробуй ещё раз:",
            parse_mode="HTML",
        )
        return ENTER_SYMBOL

    from sqlalchemy import text
    with engine.connect() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM symbols WHERE symbol = :s AND is_active = true"),
            {"s": symbol},
        ).first()

    if not exists:
        await update.message.reply_text(
            f"❌ Символ <code>{symbol}</code> не найден в базе.\n\n"
            "Проверь правильность написания или выбери из списка:",
            parse_mode="HTML",
            reply_markup=_symbol_keyboard(),
        )
        return CHOOSE_SYMBOL

    context.user_data["symbol"] = symbol

    await update.message.reply_text(
        f"📊 <b>Simulation — {symbol}</b>\n\n"
        "Выбери сторону стратегии:",
        parse_mode="HTML",
        reply_markup=_side_keyboard(),
    )
    return CHOOSE_SIDE

# ---------------------------------------------------------------------------
# Шаг 3 — выбор стороны
# ---------------------------------------------------------------------------

async def choose_side(update, context) -> int:
    query = update.callback_query
    await query.answer()

    side = query.data.split(":")[1]
    context.user_data["side"] = side

    side_label = (
        "📈 Long spot / Short futures"
        if side == "SHORT"
        else "📉 Short spot / Long futures"
    )

    await query.edit_message_text(
        f"📊 <b>Simulation — {context.user_data['symbol']}</b>\n"
        f"{side_label}\n\n"
        "Выбери сумму или напиши свою:\n"
        f"<i>от {MIN_NOTIONAL} до {MAX_NOTIONAL:,} USDT</i>",
        parse_mode="HTML",
        reply_markup=_amount_keyboard(),
    )
    return ENTER_AMOUNT

# ---------------------------------------------------------------------------
# Шаг 4 — ввод суммы текстом
# ---------------------------------------------------------------------------

MIN_NOTIONAL = 10
MAX_NOTIONAL = 100_000

async def enter_amount(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:

    raw = update.message.text.strip()

    try:
        amount = float(raw.replace(",", ".").replace(" ", ""))
        if amount <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text(
            "❌ Введи корректную сумму — положительное число.\n"
            "Например: <code>1000</code>",
            parse_mode="HTML",
        )
        return ENTER_AMOUNT

    if amount < MIN_NOTIONAL:
        await update.message.reply_text(
            f"❌ Минимальная сумма: <code>{MIN_NOTIONAL} USDT</code>",
            parse_mode="HTML",
        )
        return ENTER_AMOUNT

    if amount > MAX_NOTIONAL:
        await update.message.reply_text(
            f"❌ Максимальная сумма: <code>{MAX_NOTIONAL:,} USDT</code>",
            parse_mode="HTML",
        )
        return ENTER_AMOUNT

    context.user_data["notional"] = amount

    await update.message.reply_text(
        f"📊 <b>Simulation — {context.user_data['symbol']}</b>\n"
        f"💵 Notional: <code>{amount:,.2f} USDT</code>\n\n"
        "Выбери период:",
        parse_mode="HTML",
        reply_markup=_period_keyboard(),
    )
    return CHOOSE_PERIOD

def _amount_keyboard() -> InlineKeyboardMarkup:
    """Кнопки пресетов — пользователь может нажать ИЛИ написать текстом."""
    buttons = [
        InlineKeyboardButton(f"${a:,}", callback_data=f"sim_amount:{a}")
        for a in PRESET_AMOUNTS
    ]
    return InlineKeyboardMarkup([
        buttons[:3],   # 100 / 500 / 1000
        buttons[3:],   # 2000 / 5000
        [
            InlineKeyboardButton("◀️ Назад",        callback_data="sim_back_to_side"),
            InlineKeyboardButton("🏠 Главное меню", callback_data="sim_menu"),
        ],
    ])

# Новый handler — нажали на пресет
async def choose_preset_amount(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:

    query  = update.callback_query
    await query.answer()

    amount = float(query.data.split(":")[1])
    context.user_data["notional"] = amount

    await query.edit_message_text(
        f"📊 <b>Simulation — {context.user_data['symbol']}</b>\n"
        f"💵 Notional: <code>{amount:,.0f} USDT</code>\n\n"
        "Выбери период:",
        parse_mode="HTML",
        reply_markup=_period_keyboard(),
    )
    return CHOOSE_PERIOD

# ---------------------------------------------------------------------------
# Шаг 5 — выбор периода → расчёт → результат
# ---------------------------------------------------------------------------

async def choose_period(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    engine,
) -> int:

    query    = update.callback_query
    await query.answer()

    days     = int(query.data.split(":")[1])
    symbol   = context.user_data["symbol"]
    notional = context.user_data["notional"]
    side     = context.user_data["side"]

    await query.edit_message_text(
        f"⏳ Считаю симуляцию для <b>{symbol}</b>...",
        parse_mode="HTML",
    )

    try:
        summary, history = calculate_simulation(
            engine=engine,
            symbol=symbol,
            notional_usdt=notional,
            days=days,
            side=side,
        )
    except Exception as e:
        logger.error(f"[simulate] calculation failed for {symbol}: {e}")
        await query.message.reply_text(
            "❌ Ошибка при расчёте. Попробуй ещё раз: /simulate",
            parse_mode="HTML",
        )
        return ConversationHandler.END

    # Нет данных — возврат к выбору символа
    if summary is None:
        await query.message.reply_text(
            f"📭 Нет данных по <b>{symbol}</b> за <b>{days}д</b>.\n\n"
            "Выбери другой символ:",
            parse_mode="HTML",
            reply_markup=_symbol_keyboard(),
        )
        return CHOOSE_SYMBOL

    # Сохраняем для кнопки "Сохранить в профиль"
    context.user_data["last_summary"] = summary

    # Результат: текст
    await query.message.reply_text(
        format_simulation_summary(summary),
        parse_mode="HTML",
    )

    # Результат: график
    buf = plot_simulation(summary, history)
    await query.message.reply_photo(
        photo=buf,
        reply_markup=_result_keyboard(),
    )

    logger.info(
        f"[simulate] done | user={update.effective_user.id} "
        f"symbol={symbol} days={days} notional={notional} "
        f"total_pnl={summary['total_pnl']:+.2f}"
    )

    return ConversationHandler.END


async def back_to_symbol(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:

    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        "📊 <b>Simulation</b>\n\nВыбери символ:",
        parse_mode="HTML",
        reply_markup=_symbol_keyboard(),
    )
    return CHOOSE_SYMBOL


# Назад → выбор стороны
async def back_to_side(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:

    query  = update.callback_query
    symbol = context.user_data.get("symbol", "")
    await query.answer()

    await query.edit_message_text(
        f"📊 <b>Simulation — {symbol}</b>\n\n"
        "Выбери сторону стратегии:",
        parse_mode="HTML",
        reply_markup=_side_keyboard(),
    )
    return CHOOSE_SIDE


# Назад → ввод суммы (из CHOOSE_PERIOD)
async def back_to_amount(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:

    query  = update.callback_query
    symbol = context.user_data.get("symbol", "")
    await query.answer()

    await query.edit_message_text(
        f"📊 <b>Simulation — {symbol}</b>\n\n"
        "Введи сумму в USDT (например: <code>1000</code>):\n"
        f"<i>от {MIN_NOTIONAL} до {MAX_NOTIONAL:,} USDT</i>",
        parse_mode="HTML",
    )
    return ENTER_AMOUNT

# ---------------------------------------------------------------------------
# Сохранение в профиль
# ---------------------------------------------------------------------------

async def save_to_profile(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    engine,
) -> None:

    query       = update.callback_query
    telegram_id = update.effective_user.id
    summary     = context.user_data.get("last_summary")

    await query.answer()

    if not summary:
        await query.answer(
            "❌ Нет данных для сохранения — запусти симуляцию заново",
            show_alert=True,
        )
        return

    try:
        from app.bots.funding_bot.queries.simulation import save_simulation
        sim_id = save_simulation(engine, telegram_id, summary)

        await query.edit_message_reply_markup(reply_markup=_saved_keyboard())

        await query.message.reply_text(
            "✅ Симуляция сохранена в профиль.\n"
            "Смотри: /profile",
            parse_mode="HTML",
        )

        logger.info(f"[simulate] saved sim_id={sim_id} for user={telegram_id}")

    except Exception as e:
        logger.error(f"[simulate] save failed: {e}")
        await query.answer("❌ Ошибка при сохранении", show_alert=True)

# ---------------------------------------------------------------------------
# Отмена через /cancel
# ---------------------------------------------------------------------------

async def cancel(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:

    context.user_data.clear()
    await update.message.reply_text(
        "❌ Симуляция отменена.\n\nНачать заново: /simulate",
        parse_mode="HTML",
    )
    return ConversationHandler.END

async def _go_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    from app.bots.funding_bot.handlers.start import _main_menu_keyboard

    context.user_data.clear()

    if update.callback_query:
        await update.callback_query.message.reply_text(
            "🏠 <b>Главное меню</b>",
            parse_mode="HTML",
            reply_markup=_main_menu_keyboard(),
        )
    else:
        await update.message.reply_text(
            "🏠 <b>Главное меню</b>",
            parse_mode="HTML",
            reply_markup=_main_menu_keyboard(),
        )

    return ConversationHandler.END

def build_simulate_handler(engine) -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            CommandHandler("simulate", simulate_start),
            CallbackQueryHandler(simulate_start, pattern="^sim_restart$"),
            CallbackQueryHandler(simulate_start, pattern="^menu_simulate$"),
        ],
        states={
            CHOOSE_SYMBOL: [
                CallbackQueryHandler(choose_symbol,     pattern="^sim_symbol:"),
                CallbackQueryHandler(ask_manual_symbol, pattern="^sim_symbol_manual$"),
                CallbackQueryHandler(_go_to_menu,       pattern="^sim_menu$"),
            ],
            ENTER_SYMBOL: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    lambda u, c: enter_symbol_manual(u, c, engine),
                ),
                CallbackQueryHandler(_go_to_menu, pattern="^sim_menu$"),
            ],
            CHOOSE_SIDE: [
                CallbackQueryHandler(choose_side,    pattern="^sim_side:"),
                CallbackQueryHandler(back_to_symbol, pattern="^sim_back_to_symbol$"),
                CallbackQueryHandler(_go_to_menu,    pattern="^sim_menu$"),
            ],
            ENTER_AMOUNT: [
                # ✅ Пресеты (кнопки)
                CallbackQueryHandler(
                    choose_preset_amount,
                    pattern="^sim_amount:",
                ),
                # ✅ Текстовый ввод
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    enter_amount,
                ),
                CallbackQueryHandler(back_to_side, pattern="^sim_back_to_side$"),
                CallbackQueryHandler(_go_to_menu,  pattern="^sim_menu$"),
            ],
            CHOOSE_PERIOD: [
                CallbackQueryHandler(
                    lambda u, c: choose_period(u, c, engine),
                    pattern="^sim_period:",
                ),
                CallbackQueryHandler(back_to_amount, pattern="^sim_back_to_amount$"),
                CallbackQueryHandler(_go_to_menu,    pattern="^sim_menu$"),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CallbackQueryHandler(_go_to_menu, pattern="^sim_menu$"),
        ],
        per_user=True,
        per_chat=True,
    )