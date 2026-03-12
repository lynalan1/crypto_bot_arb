import asyncio
import logging
from telegram.ext import Application, CallbackQueryHandler
from app.bots.funding_bot.handlers.start     import register_start_handlers
from app.bots.funding_bot.handlers.positions import build_positions_handler
from app.bots.funding_bot.handlers.funding   import register_funding_handlers
from app.bots.funding_bot.handlers.analytics import build_analytics_handler
from app.bots.funding_bot.handlers.profile   import register_profile_handlers
from app.bots.funding_bot.handlers.screener  import build_screener_handler
from app.bots.funding_bot.handlers.simulate  import (
    build_simulate_handler,
    save_to_profile,
)
from app.bots.funding_bot.handlers.start import (
    register_start_handlers,
    set_lang_callback,
)

logger = logging.getLogger(__name__)


async def _noop(update, context):
    await update.callback_query.answer()


async def _go_menu_callback(update, context, engine):
    from app.bots.funding_bot.handlers.start import _main_menu_keyboard
    from app.bots.funding_bot.utils import get_lang
    from app.bots.funding_bot.i18n import t

    query = update.callback_query
    await query.answer()
    lang = get_lang(context, engine, query.from_user.id)

    await query.message.reply_text(
        t(lang, "main_menu"),
        parse_mode="HTML",
        reply_markup=_main_menu_keyboard(lang),
    )


def build_app(token: str, engine) -> Application:
    app = Application.builder().token(token).build()


    app.add_handler(build_simulate_handler(engine))
    app.add_handler(build_positions_handler(engine))
    app.add_handler(build_analytics_handler(engine))   
    app.add_handler(build_screener_handler(engine))

    
    app.add_handler(CallbackQueryHandler(
        lambda u, c: set_lang_callback(u, c, engine),
        pattern="^set_lang:",
    ))
    app.add_handler(CallbackQueryHandler(
        lambda u, c: save_to_profile(u, c, engine),
        pattern="^sim_save$",
    ))
    app.add_handler(CallbackQueryHandler(
        _noop,
        pattern="^sim_saved_noop$",
    ))
    app.add_handler(CallbackQueryHandler(
        lambda u, c: _go_menu_callback(u, c, engine),
        pattern="^go_menu$",
    ))

    
    register_start_handlers(app, engine)
    register_funding_handlers(app, engine)
    register_profile_handlers(app, engine)

    return app


async def run_bot(engine) -> None:
    from config import TELEGRAM_TOKEN
    from telegram import BotCommand

    app = build_app(TELEGRAM_TOKEN, engine)

    await app.initialize()
    await app.start()

    await app.bot.set_my_commands([
        BotCommand("menu",      "📋 Главное меню"),
        BotCommand("positions", "⏰ Следующая выплата по символу"),
        BotCommand("funding",   "📊 Топ символов по funding rate"),
        BotCommand("screener",  "🔍 Найти символы по критериям"),
        BotCommand("simulate",  "🧮 Симуляция стратегии арбитража"),
        BotCommand("stats",     "📈 Аналитика по символу"),
        BotCommand("profile",   "👤 История моих симуляций"),
        BotCommand("about",     "📚 Как работает стратегия"),
        BotCommand("help",      "❓ Список всех команд"),
    ])

    await app.updater.start_polling(drop_pending_updates=True)
    logger.info("[bot] polling started")

    try:
        await asyncio.Event().wait()
    except asyncio.CancelledError:
        pass
    finally:
        logger.info("[bot] shutting down...")
        await app.updater.stop()
        await app.stop()
        await app.shutdown()
        logger.info("[bot] shutdown complete")