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
        (
            "📚 <b>Funding Rate Arbitrage</b>\n"
            "<i>Page 1 of 5</i>\n\n"
            "Spot = real asset\n"
            "Futures = perpetual contract\n\n"
            "Funding payment every 8 hours.\n"
        ),
    ],
}

# start text

_START_TEXT_RU = (
    "📊 <b>Funding Rate Bot</b>\n\n"
    "Бот помогает зарабатывать на funding rate арбитраже.\n\n"
    "• Скринер\n"
    "• Funding таймер\n"
    "• Симуляция\n"
    "• Аналитика\n"
)

_START_TEXT_EN = (
    "📊 <b>Funding Rate Bot</b>\n\n"
    "Bot for funding rate arbitrage.\n"
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
    app.add_handler(CallbackQueryHandler(lambda u, c: menu_callback(u, c, engine), pattern="^menu_"))
    app.add_handler(CallbackQueryHandler(lambda u, c: open_about_callback(u, c, engine), pattern="^open_about$"))
    app.add_handler(CallbackQueryHandler(lambda u, c: about_page_callback(u, c, engine), pattern="^about_page:"))
    app.add_handler(CallbackQueryHandler(lambda u, c: about_menu_callback(u, c, engine), pattern="^about_menu$"))
    app.add_handler(CallbackQueryHandler(lambda u, c: u.callback_query.answer(), pattern="^about_noop$"))