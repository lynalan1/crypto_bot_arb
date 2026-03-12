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
from app.bots.funding_bot.formatters.simulation_fmt import format_simulation_summary, plot_simulation
from app.bots.funding_bot.utils import with_menu_button, get_lang
from app.bots.funding_bot.i18n import t

logger = logging.getLogger(__name__)

# Состояния
CHOOSE_SYMBOL, CHOOSE_SIDE, ENTER_AMOUNT, CHOOSE_PERIOD, ENTER_SYMBOL = range(5)
PRESET_AMOUNTS = [100, 500, 1000, 2000, 5000]
MIN_NOTIONAL = 10
MAX_NOTIONAL = 100_000
TOP_SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "ARBUSDT", "OPUSDT", "AVAXUSDT", "LINKUSDT"]

# Клавиатуры
def _symbol_keyboard(lang="ru"):
    buttons = [InlineKeyboardButton(s, callback_data=f"sim_symbol:{s}") for s in TOP_SYMBOLS]
    rows = [buttons[i:i+4] for i in range(0, len(buttons), 4)]
    rows.append([InlineKeyboardButton(t(lang, "btn_manual_input"), callback_data="sim_symbol_manual")])
    rows.append([InlineKeyboardButton(t(lang, "btn_menu"), callback_data="sim_menu")])
    return InlineKeyboardMarkup(rows)

def _side_keyboard(lang="ru"):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(t(lang, "sim_side_short"), callback_data="sim_side:SHORT"),
            InlineKeyboardButton(t(lang, "sim_side_long"), callback_data="sim_side:LONG"),
        ],
        [
            InlineKeyboardButton(t(lang, "btn_back"), callback_data="sim_back_to_symbol"),
            InlineKeyboardButton(t(lang, "btn_menu"), callback_data="sim_menu"),
        ],
    ])

def _amount_keyboard(lang="ru"):
    buttons = [InlineKeyboardButton(f"${a:,}", callback_data=f"sim_amount:{a}") for a in PRESET_AMOUNTS]
    return InlineKeyboardMarkup([
        buttons[:3],
        buttons[3:],
        [
            InlineKeyboardButton(t(lang, "btn_back"), callback_data="sim_back_to_side"),
            InlineKeyboardButton(t(lang, "btn_menu"), callback_data="sim_menu"),
        ],
    ])

def _period_keyboard(lang="ru"):
    periods = [("1д",1),("7д",7),("14д",14),("30д",30),("90д",90)] if lang=="ru" else [("1d",1),("7d",7),("14d",14),("30d",30),("90d",90)]
    buttons = [InlineKeyboardButton(label, callback_data=f"sim_period:{days}") for label, days in periods]
    return InlineKeyboardMarkup([
        buttons,
        [InlineKeyboardButton(t(lang, "btn_back"), callback_data="sim_back_to_amount"), InlineKeyboardButton(t(lang, "btn_menu"), callback_data="sim_menu")]
    ])

def _result_keyboard(lang="ru", saved=False):
    save_btn = InlineKeyboardButton(t(lang, "sim_saved") if saved else t(lang, "sim_save"),
                                    callback_data="sim_saved_noop" if saved else "sim_save")
    return InlineKeyboardMarkup([
        [save_btn, InlineKeyboardButton(t(lang, "sim_new"), callback_data="sim_restart")],
        [InlineKeyboardButton(t(lang, "btn_menu"), callback_data="go_menu")]
    ])

def _saved_keyboard(lang="ru"):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t(lang, "sim_saved"), callback_data="sim_saved_noop"),
         InlineKeyboardButton(t(lang, "sim_new"), callback_data="sim_restart")]
    ])

# Хендлеры
async def simulate_start(update, context, engine) -> int:
    lang = get_lang(context, engine, update.effective_user.id)
    context.user_data.clear()
    context.user_data["lang"] = lang

    reply = update.message.reply_text if update.message else update.callback_query.message.reply_text
    if not update.message:
        await update.callback_query.answer()

    await reply(t(lang, "sim_choose_symbol"), parse_mode="HTML", reply_markup=_symbol_keyboard(lang))
    return CHOOSE_SYMBOL

async def choose_symbol(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    symbol = query.data.split(":")[1].upper()
    context.user_data["symbol"] = symbol
    lang = context.user_data.get("lang", "ru")
    await query.edit_message_text(t(lang, "sim_choose_side", symbol=symbol), parse_mode="HTML", reply_markup=_side_keyboard(lang))
    return CHOOSE_SIDE

async def ask_manual_symbol(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    lang = context.user_data.get("lang", "ru")
    await query.edit_message_text(t(lang, "manual_prompt"), parse_mode="HTML")
    return ENTER_SYMBOL

async def enter_symbol_manual(update: Update, context: ContextTypes.DEFAULT_TYPE, engine) -> int:
    symbol = update.message.text.strip().upper()
    lang = context.user_data.get("lang", "ru")

    if not symbol.isalnum() or not (5 <= len(symbol) <= 12):
        await update.message.reply_text(t(lang, "invalid_symbol"), parse_mode="HTML")
        return ENTER_SYMBOL

    from sqlalchemy import text
    with engine.connect() as conn:
        exists = conn.execute(text("SELECT 1 FROM symbols WHERE symbol=:s AND is_active=true"), {"s": symbol}).first()

    if not exists:
        await update.message.reply_text(t(lang, "no_symbol_data", symbol=symbol),
                                        parse_mode="HTML",
                                        reply_markup=_symbol_keyboard(lang))
        return CHOOSE_SYMBOL

    context.user_data["symbol"] = symbol
    await update.message.reply_text(t(lang, "sim_choose_side", symbol=symbol), parse_mode="HTML",
                                    reply_markup=_side_keyboard(lang))
    return CHOOSE_SIDE

async def choose_side(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data["side"] = query.data.split(":")[1]
    symbol = context.user_data.get("symbol", "")
    lang = context.user_data.get("lang", "ru")
    side_label = t(lang, "sim_side_short") if context.user_data["side"] == "SHORT" else t(lang, "sim_side_long")

    await query.edit_message_text(
        t(lang, "sim_choose_amount", symbol=symbol, side=side_label, min=MIN_NOTIONAL, max=MAX_NOTIONAL),
        parse_mode="HTML",
        reply_markup=_amount_keyboard(lang)
    )
    return ENTER_AMOUNT

async def choose_preset_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    amount = float(query.data.split(":")[1])
    context.user_data["notional"] = amount
    lang = context.user_data.get("lang", "ru")
    symbol = context.user_data.get("symbol", "")

    await query.edit_message_text(t(lang, "sim_choose_period", symbol=symbol, amount=amount),
                                  parse_mode="HTML",
                                  reply_markup=_period_keyboard(lang))
    return CHOOSE_PERIOD

async def enter_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    raw = update.message.text.strip()
    lang = context.user_data.get("lang", "ru")
    try:
        amount = float(raw.replace(",", ".").replace(" ", ""))
        if amount <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ Введи корректную сумму — положительное число.\nНапример: <code>1000</code>",
                                        parse_mode="HTML")
        return ENTER_AMOUNT

    if amount < MIN_NOTIONAL:
        await update.message.reply_text(f"❌ Минимальная сумма: <code>{MIN_NOTIONAL} USDT</code>", parse_mode="HTML")
        return ENTER_AMOUNT
    if amount > MAX_NOTIONAL:
        await update.message.reply_text(f"❌ Максимальная сумма: <code>{MAX_NOTIONAL:,} USDT</code>", parse_mode="HTML")
        return ENTER_AMOUNT

    context.user_data["notional"] = amount
    symbol = context.user_data.get("symbol", "")
    await update.message.reply_text(t(lang, "sim_choose_period", symbol=symbol, amount=amount),
                                    parse_mode="HTML",
                                    reply_markup=_period_keyboard(lang))
    return CHOOSE_PERIOD

async def choose_period(update: Update, context: ContextTypes.DEFAULT_TYPE, engine) -> int:
    query = update.callback_query
    await query.answer()
    lang = context.user_data.get("lang", "ru")
    symbol = context.user_data["symbol"]
    days = int(query.data.split(":")[1])
    notional = context.user_data["notional"]

    await query.edit_message_text(t(lang, "sim_calculating", symbol=symbol), parse_mode="HTML")

    summary, history = calculate_simulation(engine, symbol, notional, days)
    if not summary:
        await query.message.reply_text(t(lang, "sim_no_data", symbol=symbol),
                                       parse_mode="HTML",
                                       reply_markup=with_menu_button([], lang))
        return ConversationHandler.END

    context.user_data["last_summary"] = summary
    await query.message.reply_text(format_simulation_summary(summary),
                                   parse_mode="HTML",
                                   reply_markup=_result_keyboard(lang))

    buf = plot_simulation(summary, history)
    await query.message.reply_photo(photo=buf)

    return ConversationHandler.END

async def save_to_profile(update: Update, context: ContextTypes.DEFAULT_TYPE, engine) -> None:
    query = update.callback_query
    telegram_id = update.effective_user.id
    summary = context.user_data.get("last_summary")
    lang = context.user_data.get("lang", "ru")
    await query.answer()
    if not summary:
        await query.answer("❌ Нет данных для сохранения — запусти симуляцию заново", show_alert=True)
        return
    try:
        from app.bots.funding_bot.queries.simulation import save_simulation
        sim_id = save_simulation(engine, telegram_id, summary)
        await query.edit_message_reply_markup(reply_markup=_saved_keyboard(lang))
        await query.message.reply_text("✅ Симуляция сохранена в профиль.\nСмотри: /profile", parse_mode="HTML")
        logger.info(f"[simulate] saved sim_id={sim_id} for user={telegram_id}")
    except Exception as e:
        logger.error(f"[simulate] save failed: {e}")
        await query.answer("❌ Ошибка при сохранении", show_alert=True)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text("❌ Симуляция отменена.\n\nНачать заново: /simulate", parse_mode="HTML")
    return ConversationHandler.END

# /back handlers
async def back_to_symbol(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    lang = context.user_data.get("lang", "ru")
    await query.edit_message_text(t(lang, "sim_choose_symbol"), parse_mode="HTML", reply_markup=_symbol_keyboard(lang))
    return CHOOSE_SYMBOL

async def back_to_side(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    symbol = context.user_data.get("symbol", "")
    lang = context.user_data.get("lang", "ru")
    await query.edit_message_text(t(lang, "sim_choose_side", symbol=symbol), parse_mode="HTML", reply_markup=_side_keyboard(lang))
    return CHOOSE_SIDE

async def back_to_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    symbol = context.user_data.get("symbol", "")
    lang = context.user_data.get("lang", "ru")
    side = context.user_data.get("side", "SHORT")
    side_label = t(lang, "sim_side_short") if side=="SHORT" else t(lang, "sim_side_long")
    await query.edit_message_text(
        t(lang, "sim_choose_amount", symbol=symbol, side=side_label, min=MIN_NOTIONAL, max=MAX_NOTIONAL),
        parse_mode="HTML",
        reply_markup=_amount_keyboard(lang)
    )
    return ENTER_AMOUNT

# /menu
async def _go_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    from app.bots.funding_bot.handlers.start import _main_menu_keyboard
    lang = context.user_data.get("lang", "ru")
    context.user_data.clear()
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.reply_text("🏠 <b>Главное меню</b>" if lang=="ru" else "🏠 <b>Main Menu</b>",
                                                       parse_mode="HTML",
                                                       reply_markup=_main_menu_keyboard(lang))
    else:
        await update.message.reply_text("🏠 <b>Главное меню</b>" if lang=="ru" else "🏠 <b>Main Menu</b>",
                                        parse_mode="HTML",
                                        reply_markup=_main_menu_keyboard(lang))
    return ConversationHandler.END

# /build handler
def build_simulate_handler(engine) -> ConversationHandler:
    from app.bots.funding_bot.handlers.start import _main_menu_keyboard
    return ConversationHandler(
        entry_points=[
            CommandHandler("simulate", lambda u, c: simulate_start(u, c, engine)),
            CallbackQueryHandler(lambda u, c: simulate_start(u, c, engine), pattern="^sim_restart$"),
            CallbackQueryHandler(lambda u, c: simulate_start(u, c, engine), pattern="^menu_simulate$"),
        ],
        states={
            CHOOSE_SYMBOL: [
                CallbackQueryHandler(choose_symbol, pattern="^sim_symbol:"),
                CallbackQueryHandler(ask_manual_symbol, pattern="^sim_symbol_manual$"),
                CallbackQueryHandler(_go_to_menu, pattern="^sim_menu$"),
            ],
            ENTER_SYMBOL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, lambda u, c: enter_symbol_manual(u, c, engine)),
                CallbackQueryHandler(_go_to_menu, pattern="^sim_menu$"),
            ],
            CHOOSE_SIDE: [
                CallbackQueryHandler(choose_side, pattern="^sim_side:"),
                CallbackQueryHandler(back_to_symbol, pattern="^sim_back_to_symbol$"),
                CallbackQueryHandler(_go_to_menu, pattern="^sim_menu$"),
            ],
            ENTER_AMOUNT: [
                CallbackQueryHandler(choose_preset_amount, pattern="^sim_amount:"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, enter_amount),
                CallbackQueryHandler(back_to_side, pattern="^sim_back_to_side$"),
                CallbackQueryHandler(_go_to_menu, pattern="^sim_menu$"),
            ],
            CHOOSE_PERIOD: [
                CallbackQueryHandler(lambda u,c: choose_period(u,c,engine), pattern="^sim_period:"),
                CallbackQueryHandler(back_to_amount, pattern="^sim_back_to_amount$"),
                CallbackQueryHandler(_go_to_menu, pattern="^sim_menu$"),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel), CallbackQueryHandler(_go_to_menu, pattern="^sim_menu$")],
        per_user=True,
        per_chat=True,
    )