import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler

from app.bots.funding_bot.handlers.funding import funding_command
from app.bots.funding_bot.handlers.analytics import analytics_command
from app.bots.funding_bot.handlers.profile import profile_command
from app.bots.funding_bot.utils import with_menu_button, get_lang
from app.bots.funding_bot.i18n import t

logger = logging.getLogger(__name__)

# About pages

_ABOUT_PAGES = {
    "ru": [
        (
            "📚 <b>Как работает funding rate арбитраж</b>\n"
            "<i>Страница 1 из 5 — Что такое funding rate?</i>\n\n"
            "На крипто биржах есть два рынка для одного актива:\n"
            "• <b>Spot</b> — покупаешь реальный токен\n"
            "• <b>Futures (Perp)</b> — торгуешь контрактом без даты экспирации\n\n"
            "Чтобы цена фьючерса не уходила далеко от спота — биржа каждые "
            "<b>8 часов</b> списывает или начисляет платёж между лонгами и шортами.\n"
            "Этот платёж называется <b>funding rate</b>.\n\n"
            "🟢 Rate положительный → лонги платят шортам\n"
            "🔴 Rate отрицательный → шорты платят лонгам\n"
        ),
        (
            "📚 <b>Как работает funding rate арбитраж</b>\n"
            "<i>Страница 2 из 5 — Суть стратегии</i>\n\n"
            "Идея: <b>получать funding, не рискуя направлением рынка.</b>\n\n"
            "Когда rate положительный — открываем две позиции одновременно:\n"
            "• <b>Long spot</b>\n"
            "• <b>Short futures</b>\n\n"
            "Цена растёт → спот +, фьючерс − → итог 0\n"
            "Цена падает → спот −, фьючерс + → итог 0\n"
            "Каждые 8 часов → шорт получает funding ✅\n"
        ),
        (
            "📚 <b>Как работает funding rate арбитраж</b>\n"
            "<i>Страница 3 из 5 — Математика</i>\n\n"
            "<b>Пример:</b>\n"
            "Notional: <code>10,000 USDT</code>\n"
            "Funding rate: <code>+0.01%</code>\n\n"
            "<code>10,000 × 0.0001 = 1 USDT</code>\n"
        ),
        (
            "📚 <b>Как работает funding rate арбитраж</b>\n"
            "<i>Страница 4 из 5 — Риски</i>\n\n"
            "⚠️ Rate может стать отрицательным\n"
            "⚠️ Возможна ликвидация\n"
            "⚠️ Basis риск\n"
            "⚠️ Комиссии\n"
        ),
        (
            "📚 <b>Как работает funding rate арбитраж</b>\n"
            "<i>Страница 5 из 5 — Термины</i>\n\n"
            "Funding rate, Spot, Futures, Basis, Long, Short, Notional\n"
        ),
    ],
    "en": [
    # Page 1
    (
        "📚 <b>Funding Rate Arbitrage Explained</b>\n"
        "<i>Page 1 of 5 — What is funding rate?</i>\n\n"
        "Crypto exchanges have two markets for the same asset:\n"
        "• <b>Spot</b> — you buy the actual token\n"
        "• <b>Futures (Perp)</b> — you trade a contract with no expiry date\n\n"
        "To keep the futures price close to spot, the exchange every "
        "<b>8 hours</b> charges or pays a fee between longs and shorts.\n"
        "This fee is called the <b>funding rate</b>.\n\n"
        "🟢 Positive rate → longs pay shorts\n"
        "🔴 Negative rate → shorts pay longs\n"
    ),
    # Page 2
    (
        "📚 <b>Funding Rate Arbitrage Explained</b>\n"
        "<i>Page 2 of 5 — Strategy overview</i>\n\n"
        "The idea: <b>earn funding without taking market direction risk.</b>\n\n"
        "When rate is positive — open two positions simultaneously:\n"
        "• <b>Long spot</b> — buy the token on spot\n"
        "• <b>Short futures</b> — sell a futures contract for the same amount\n\n"
        "What happens:\n"
        "• Price rises → spot gains, futures loses → <b>net: 0</b>\n"
        "• Price drops → spot loses, futures gains → <b>net: 0</b>\n"
        "• Every 8 hours → short receives funding payment ✅\n\n"
        "Positions hedge each other — market risk is <b>neutralized</b>.\n"
    ),
    # Page 3
    (
        "📚 <b>Funding Rate Arbitrage Explained</b>\n"
        "<i>Page 3 of 5 — The math</i>\n\n"
        "<b>Example with ETHUSDT:</b>\n\n"
        "Notional: <code>10,000 USDT</code>\n"
        "Funding rate: <code>+0.01%</code> every 8 hours\n\n"
        "Income per payment:\n"
        "<code>10,000 × 0.0001 = 1 USDT</code>\n\n"
        "Per day (3 payments):\n"
        "<code>1 × 3 = 3 USDT</code>\n\n"
        "Per month (90 payments):\n"
        "<code>1 × 90 = 90 USDT → 0.9% per month</code>\n\n"
        "Entry + exit fees:\n"
        "<code>10,000 × 0.001 × 2 = 20 USDT</code>\n\n"
        "Net profit: <code>90 - 20 = 70 USDT (~8.4% annual)</code>\n"
    ),
    # Page 4
    (
        "📚 <b>Funding Rate Arbitrage Explained</b>\n"
        "<i>Page 4 of 5 — Risks</i>\n\n"
        "<b>The strategy is not risk-free. Main risks:</b>\n\n"
        "⚠️ <b>Rate goes negative</b>\n"
        "You opened at +0.01%, rate became -0.005% — now you're paying.\n"
        "Solution: monitor rate and close position when sign changes.\n\n"
        "⚠️ <b>Futures liquidation</b>\n"
        "Sharp price moves can trigger a margin call on the short.\n"
        "Solution: no leverage, keep margin buffer.\n\n"
        "⚠️ <b>Basis risk</b>\n"
        "Spot and futures prices can temporarily diverge.\n\n"
        "⚠️ <b>Fees eat profits</b>\n"
        "On small amounts and short periods, fees &gt; funding.\n"
        "Solution: hold position long enough, use maker orders.\n\n"
        "✅ Use /screener and /simulate to find symbols with "
        "the best risk/reward ratio.\n"
    ),
    # Page 5
    (
        "📚 <b>Funding Rate Arbitrage Explained</b>\n"
        "<i>Page 5 of 5 — Glossary</i>\n\n"
        "🔤 <b>Funding rate</b>\n"
        "% that longs pay shorts (or vice versa) every 8 hours.\n"
        "Higher = more profitable to be short on futures.\n\n"
        "🔤 <b>Spot</b>\n"
        "Market where you buy the actual token.\n"
        "Price here is the real price of the asset.\n\n"
        "🔤 <b>Futures / Perp (Perpetual)</b>\n"
        "Contract to buy/sell an asset with no expiry.\n"
        "Price is anchored to spot via funding rate.\n\n"
        "🔤 <b>Basis</b>\n"
        "Difference between futures and spot price.\n"
        "Small basis = good peg = less slippage risk at close.\n\n"
        "🔤 <b>Long / Short</b>\n"
        "Long — betting on price rise. Short — betting on fall.\n"
        "In our strategy long spot + short futures neutralize direction.\n\n"
        "🔤 <b>Notional</b>\n"
        "Position size in USDT. Funding is calculated from this.\n\n"
        "🔤 <b>Positive ratio</b>\n"
        "Share of time the rate was positive.\n"
        "90% = out of 90 payments you received money 81 times.\n\n"
        "🔤 <b>PnL (Profit and Loss)</b>\n"
        "Final profit or loss from the strategy.\n\n"
        "🔤 <b>Liquidation</b>\n"
        "Forced position close by exchange due to insufficient margin.\n"
        "Avoided in our strategy by using no leverage.\n\n"
        "🔤 <b>Maker / Taker</b>\n"
        "Maker — limit order (cheaper fee).\n"
        "Taker — market order (higher fee).\n"
        "Fees: maker ~0.02%, taker ~0.05% on Binance Futures.\n"
    ),
],

}

# start text

_START_TEXT_RU = (
    "📊 <b>Funding Rate Bot</b>\n\n"
    "Бот помогает зарабатывать на <b>funding rate арбитраже</b> — "
    "нейтральной к рынку стратегии на крипто биржах.\n\n"
    "• 🔍 Скринер лучших символов по доходности\n"
    "• ⏰ Таймер до следующей выплаты funding\n"
    "• 🧮 Симуляция стратегии на исторических данных\n"
    "• 📈 Аналитика basis и спредов\n"
)

_START_TEXT_EN = (
    "📊 <b>Funding Rate Bot</b>\n\n"
    "Earn on <b>funding rate arbitrage</b> — "
    "a market-neutral strategy on crypto exchanges.\n\n"
    "• 🔍 Screener for top symbols by yield\n"
    "• ⏰ Countdown to next funding payment\n"
    "• 🧮 Strategy simulation on historical data\n"
    "• 📈 Basis and spread analytics\n"
)

# keyboards

def _about_keyboard(page: int, lang: str = "ru") -> InlineKeyboardMarkup:
    total = len(_ABOUT_PAGES[lang])
    nav = []

    if page > 0:
        nav.append(InlineKeyboardButton("◀️", callback_data=f"about_page:{page-1}"))

    nav.append(InlineKeyboardButton(f"{page+1}/{total}", callback_data="about_noop"))

    if page < total - 1:
        nav.append(InlineKeyboardButton("▶️", callback_data=f"about_page:{page+1}"))

    return InlineKeyboardMarkup([
        nav,
        [InlineKeyboardButton(t(lang, "btn_menu"), callback_data="about_menu")]
    ])


def _main_menu_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(t(lang, "btn_positions"), callback_data="menu_positions"),
            InlineKeyboardButton(t(lang, "btn_screener"), callback_data="menu_screener"),
        ],
        [
            InlineKeyboardButton(t(lang, "btn_funding"), callback_data="menu_funding"),
            InlineKeyboardButton(t(lang, "btn_analytics"), callback_data="menu_analytics"),
        ],
        [
            InlineKeyboardButton(t(lang, "btn_simulate"), callback_data="menu_simulate"),
            InlineKeyboardButton(t(lang, "btn_profile"), callback_data="menu_profile"),
        ],
        [
            InlineKeyboardButton(t(lang, "btn_about"), callback_data="open_about"),
        ],
    ])

# /start

async def start_command(update: Update) -> None:

    user = update.effective_user
    name = user.first_name or user.username or "there"

    greeting = (
        f"👋 <b>{name}</b>!\n\n"
        f"{_START_TEXT_RU}\n"
        "────────────\n\n"
        f"{_START_TEXT_EN}\n"
        "🌐 Choose language:"
    )

    await update.message.reply_text(
        greeting,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🇷🇺 Русский", callback_data="set_lang:ru"),
                InlineKeyboardButton("🇬🇧 English", callback_data="set_lang:en"),
            ]
        ])
    )

# /menu

async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE, engine) -> None:
    lang = get_lang(context, engine, update.effective_user.id)

    await update.message.reply_text(
        t(lang, "main_menu"),
        parse_mode="HTML",
        reply_markup=_main_menu_keyboard(lang)
    )

# /help

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE, engine) -> None:
    lang = get_lang(context, engine, update.effective_user.id)

    text = (
        f"{t(lang,'help_title')}\n\n"
        f"{t(lang,'help_positions')}\n\n"
        f"{t(lang,'help_funding')}\n\n"
        f"{t(lang,'help_screener')}\n\n"
        f"{t(lang,'help_stats')}\n\n"
        f"{t(lang,'help_simulate')}\n\n"
        f"{t(lang,'help_profile')}\n\n"
        f"{t(lang,'help_about')}\n\n"
        f"{t(lang,'help_menu')}\n"
    )

    await update.message.reply_text(
        text,
        parse_mode="HTML",
        reply_markup=with_menu_button([], lang)
    )

# /about

async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE, engine) -> None:
    lang = get_lang(context, engine, update.effective_user.id)

    await update.message.reply_text(
        _ABOUT_PAGES[lang][0],
        parse_mode="HTML",
        reply_markup=_about_keyboard(0, lang)
    )

# callbacks

async def open_about_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, engine) -> None:
    query = update.callback_query
    await query.answer()

    lang = get_lang(context, engine, query.from_user.id)

    await query.message.reply_text(
        _ABOUT_PAGES[lang][0],
        parse_mode="HTML",
        reply_markup=_about_keyboard(0, lang)
    )


async def about_page_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, engine) -> None:
    query = update.callback_query
    await query.answer()

    page = int(query.data.split(":")[1])
    lang = get_lang(context, engine, query.from_user.id)

    await query.edit_message_text(
        _ABOUT_PAGES[lang][page],
        parse_mode="HTML",
        reply_markup=_about_keyboard(page, lang)
    )


async def about_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, engine) -> None:
    query = update.callback_query
    await query.answer()

    lang = get_lang(context, engine, query.from_user.id)

    await query.message.reply_text(
        t(lang, "main_menu"),
        parse_mode="HTML",
        reply_markup=_main_menu_keyboard(lang)
    )


async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, engine) -> None:
    query = update.callback_query
    await query.answer()

    handlers = {
        "menu_funding": lambda: funding_command(update, context, engine),
        "menu_analytics": lambda: analytics_command(update, context),
        "menu_profile": lambda: profile_command(update, context, engine),
    }

    fn = handlers.get(query.data)
    if fn:
        await fn()


async def set_lang_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, engine) -> None:

    from app.bots.funding_bot.queries.lang import set_user_lang

    query = update.callback_query
    lang = query.data.split(":")[1]

    await query.answer()

    set_user_lang(engine, query.from_user.id, lang)
    context.user_data["lang"] = lang

    confirmed = "✅ Language set" if lang == "en" else "✅ Язык установлен"

    await query.edit_message_text(confirmed)

    await query.message.reply_text(
        t(lang, "main_menu"),
        parse_mode="HTML",
        reply_markup=_main_menu_keyboard(lang)
    )

# register

def register_start_handlers(app, engine):

    app.add_handler(CommandHandler("start", lambda u, c: start_command(u)))
    app.add_handler(CommandHandler("menu", lambda u, c: menu_command(u, c, engine)))
    app.add_handler(CommandHandler("help", lambda u, c: help_command(u, c, engine)))
    app.add_handler(CommandHandler("about", lambda u, c: about_command(u, c, engine)))

    app.add_handler(CallbackQueryHandler(lambda u, c: set_lang_callback(u, c, engine), pattern="^set_lang:"))
    app.add_handler(CallbackQueryHandler(lambda u, c: menu_callback(u, c, engine), pattern="^menu_(funding|analytics|profile)$"))
    app.add_handler(CallbackQueryHandler(lambda u, c: open_about_callback(u, c, engine), pattern="^open_about$"))
    app.add_handler(CallbackQueryHandler(lambda u, c: about_page_callback(u, c, engine), pattern="^about_page:"))
    app.add_handler(CallbackQueryHandler(lambda u, c: about_menu_callback(u, c, engine), pattern="^about_menu$"))
    app.add_handler(CallbackQueryHandler(lambda u, c: u.callback_query.answer(), pattern="^about_noop$"))

    