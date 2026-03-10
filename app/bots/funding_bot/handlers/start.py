import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler

from app.bots.funding_bot.handlers.positions import positions_command
from app.bots.funding_bot.handlers.pnl       import pnl_command
from app.bots.funding_bot.handlers.funding   import funding_command
from app.bots.funding_bot.handlers.analytics import analytics_command
from app.bots.funding_bot.handlers.profile   import profile_command

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Клавиатура главного меню — используется везде
# ---------------------------------------------------------------------------

def _main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📊 Positions",  callback_data="menu_positions"),
            InlineKeyboardButton("💰 PnL",         callback_data="menu_pnl"),
        ],
        [
            InlineKeyboardButton("⚡ Funding",     callback_data="menu_funding"),
            InlineKeyboardButton("📈 Analytics",   callback_data="menu_analytics"),
        ],
        [
            InlineKeyboardButton("🧮 Simulate",    callback_data="menu_simulate"),
            InlineKeyboardButton("👤 Profile",     callback_data="menu_profile"),
        ],
        [
            InlineKeyboardButton("📚 Как это работает", callback_data="menu_about"),
        ],
    ])

# ---------------------------------------------------------------------------
# /start — приветствие + меню
# ---------------------------------------------------------------------------

async def start_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:

    user = update.effective_user
    name = user.first_name or user.username or "there"

    logger.info(f"[start] user={user.id} username={user.username}")

    await update.message.reply_text(
        f"👋 Hey, <b>{name}</b>!\n"
        "\n"
        "Это бот для анализа <b>funding rate арбитража</b>.\n"
        "Данные собираются в реальном времени с Binance.\n",
        parse_mode="HTML",
        reply_markup=_main_menu_keyboard(),
    )

# ---------------------------------------------------------------------------
# /menu — только клавиатура без приветствия
# ---------------------------------------------------------------------------

async def menu_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:

    await update.message.reply_text(
        "📋 <b>Главное меню</b>",
        parse_mode="HTML",
        reply_markup=_main_menu_keyboard(),
    )

# ---------------------------------------------------------------------------
# /help
# ---------------------------------------------------------------------------

async def help_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:

    await update.message.reply_text(
        "📖 <b>Команды</b>\n"
        "\n"
        "/menu       — главное меню\n"
        "/positions  — открытые позиции\n"
        "/pnl        — сводка PnL\n"
        "/funding    — топ funding rate\n"
        "/stats      — аналитика по символу\n"
        "/simulate   — симуляция стратегии\n"
        "/profile    — история симуляций\n"
        "/about      — как работает стратегия\n"
        "/cancel     — отменить текущий диалог\n"
        "/help       — это сообщение\n",
        parse_mode="HTML",
        reply_markup=_main_menu_keyboard(),
    )

# ---------------------------------------------------------------------------
# /about — объяснение стратегии
# ---------------------------------------------------------------------------

_ABOUT_PAGES = [

    # Страница 1 — что такое funding rate
    (
        "📚 <b>Как работает funding rate арбитраж</b>\n"
        "<i>Страница 1 из 4 — Что такое funding rate?</i>\n"
        "\n"
        "На крипто биржах есть два рынка для одного актива:\n"
        "• <b>Spot</b> — покупаешь реальный токен\n"
        "• <b>Futures (Perp)</b> — торгуешь контрактом без даты экспирации\n"
        "\n"
        "Чтобы цена фьючерса не уходила далеко от спота — биржа каждые "
        "<b>8 часов</b> списывает или начисляет платёж между лонгами и шортами.\n"
        "Этот платёж называется <b>funding rate</b>.\n"
        "\n"
        "🟢 Rate положительный → лонги платят шортам\n"
        "🔴 Rate отрицательный → шорты платят лонгам\n"
    ),

    # Страница 2 — суть арбитража
    (
        "📚 <b>Как работает funding rate арбитраж</b>\n"
        "<i>Страница 2 из 4 — Суть стратегии</i>\n"
        "\n"
        "Идея простая: <b>получать funding, не рискуя направлением рынка.</b>\n"
        "\n"
        "Когда rate положительный — открываем две позиции одновременно:\n"
        "• <b>Long spot</b> — покупаем токен на споте\n"
        "• <b>Short futures</b> — продаём фьючерс на ту же сумму\n"
        "\n"
        "Что происходит:\n"
        "• Цена растёт → спот в плюсе, фьючерс в минусе → <b>итог: 0</b>\n"
        "• Цена падает → спот в минусе, фьючерс в плюсе → <b>итог: 0</b>\n"
        "• Каждые 8 часов → шорт получает funding payment ✅\n"
        "\n"
        "Позиции взаимно хеджируют друг друга — рыночный риск <b>нейтрализован</b>.\n"
        "Зарабатываешь только на funding.\n"
    ),

    # Страница 3 — математика
    (
        "📚 <b>Как работает funding rate арбитраж</b>\n"
        "<i>Страница 3 из 4 — Математика</i>\n"
        "\n"
        "<b>Пример с ETHUSDT:</b>\n"
        "\n"
        "Notional: <code>10,000 USDT</code>\n"
        "Funding rate: <code>+0.01%</code> каждые 8 часов\n"
        "\n"
        "Доход за одну выплату:\n"
        "<code>10,000 × 0.0001 = 1 USDT</code>\n"
        "\n"
        "За день (3 выплаты):\n"
        "<code>1 × 3 = 3 USDT</code>\n"
        "\n"
        "За месяц (90 выплат):\n"
        "<code>1 × 90 = 90 USDT → 0.9% за месяц</code>\n"
        "\n"
        "Комиссии при входе и выходе:\n"
        "<code>10,000 × 0.001 × 2 = 20 USDT</code>\n"
        "\n"
        "Чистая прибыль за месяц: <code>90 - 20 = 70 USDT</code>\n"
        "Доходность: <code>~0.7% в месяц → ~8.4% годовых</code>\n"
        "\n"
        "⚡ Это при <i>среднем</i> rate. Топ символы дают 0.05-0.1% → "
        "доходность кратно выше.\n"
    ),

    # Страница 4 — риски
    (
        "📚 <b>Как работает funding rate арбитраж</b>\n"
        "<i>Страница 4 из 4 — Риски</i>\n"
        "\n"
        "<b>Стратегия не безрисковая. Главные риски:</b>\n"
        "\n"
        "⚠️ <b>Rate уходит в минус</b>\n"
        "Ты открылся при +0.01%, rate стал -0.005% — теперь ты платишь.\n"
        "Решение: мониторить rate и закрывать позицию при смене знака.\n"
        "\n"
        "⚠️ <b>Liquidation риск на фьючерсе</b>\n"
        "При резком движении цены шорт может получить margin call.\n"
        "Решение: не использовать плечо, держать запас маржи.\n"
        "\n"
        "⚠️ <b>Basis риск</b>\n"
        "Спот и фьючерс могут временно расходиться в цене.\n"
        "При закрытии позиции это может дать слиппаж.\n"
        "\n"
        "⚠️ <b>Комиссии съедают прибыль</b>\n"
        "На малых суммах и коротких периодах fees > funding.\n"
        "Решение: держать позицию достаточно долго, "
        "использовать maker orders.\n"
        "\n"
        "✅ Этот бот помогает найти символы с <b>стабильно высоким</b> "
        "rate и посчитать реальную доходность через /simulate.\n"
    ),
]


def _about_keyboard(page: int) -> InlineKeyboardMarkup:
    total = len(_ABOUT_PAGES)
    nav   = []

    if page > 0:
        nav.append(InlineKeyboardButton("◀️", callback_data=f"about_page:{page - 1}"))

    nav.append(InlineKeyboardButton(f"{page + 1}/{total}", callback_data="about_noop"))

    if page < total - 1:
        nav.append(InlineKeyboardButton("▶️", callback_data=f"about_page:{page + 1}"))

    return InlineKeyboardMarkup([
        nav,
        [InlineKeyboardButton("🏠 Главное меню", callback_data="about_menu")],
    ])


async def about_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:

    if update.message:
        await update.message.reply_text(
            _ABOUT_PAGES[0],
            parse_mode="HTML",
            reply_markup=_about_keyboard(0),
        )
    else:
        query = update.callback_query
        await query.answer()
        await query.message.reply_text(
            _ABOUT_PAGES[0],
            parse_mode="HTML",
            reply_markup=_about_keyboard(0),
        )


async def about_page_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:

    query = update.callback_query
    page  = int(query.data.split(":")[1])
    await query.answer()

    await query.edit_message_text(
        _ABOUT_PAGES[page],
        parse_mode="HTML",
        reply_markup=_about_keyboard(page),
    )


async def about_menu_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:

    query = update.callback_query
    await query.answer()
    await query.edit_message_reply_markup(reply_markup=None)

    await query.message.reply_text(
        "📋 <b>Главное меню</b>",
        parse_mode="HTML",
        reply_markup=_main_menu_keyboard(),
    )

# ---------------------------------------------------------------------------
# Обработка кнопок главного меню
# ---------------------------------------------------------------------------

async def menu_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    engine,
) -> None:

    query = update.callback_query
    await query.answer()
    await query.edit_message_reply_markup(reply_markup=None)

    handlers = {
    "menu_pnl":       lambda: pnl_command(update, context, engine),
    "menu_funding":   lambda: funding_command(update, context, engine),
    "menu_analytics": lambda: analytics_command(update, context),
    "menu_profile":   lambda: profile_command(update, context, engine),
    "menu_about":     lambda: about_command(update, context),
}

    fn = handlers.get(query.data)
    if fn:
        await fn()

# ---------------------------------------------------------------------------
# Регистрация
# ---------------------------------------------------------------------------

def register_start_handlers(app, engine) -> None:
    from telegram.ext import CallbackQueryHandler

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("menu",  menu_command))
    app.add_handler(CommandHandler("help",  help_command))
    app.add_handler(CommandHandler("about", about_command))

    app.add_handler(CallbackQueryHandler(
        lambda u, c: menu_callback(u, c, engine),
        pattern="^menu_",
    ))
    app.add_handler(CallbackQueryHandler(
        about_page_callback,
        pattern="^about_page:",
    ))
    app.add_handler(CallbackQueryHandler(
        about_menu_callback,
        pattern="^about_menu$",
    ))
    app.add_handler(CallbackQueryHandler(
        lambda u, c: u.callback_query.answer(),
        pattern="^about_noop$",
    ))
