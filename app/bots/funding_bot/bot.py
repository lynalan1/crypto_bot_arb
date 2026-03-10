import asyncio
import logging
from telegram.ext import Application, CallbackQueryHandler
from app.bots.funding_bot.utils import with_menu_button
from app.bots.funding_bot.handlers.start     import register_start_handlers
from app.bots.funding_bot.handlers.positions import build_positions_handler
from app.bots.funding_bot.handlers.pnl       import register_pnl_handlers
from app.bots.funding_bot.handlers.funding   import register_funding_handlers
from app.bots.funding_bot.handlers.analytics import register_analytics_handlers
from app.bots.funding_bot.handlers.profile   import register_profile_handlers
from app.bots.funding_bot.handlers.simulate  import (
    build_simulate_handler,
    save_to_profile,
)

logger = logging.getLogger(__name__)


async def _noop(update, context):
    await update.callback_query.answer()

from app.bots.funding_bot.utils import with_menu_button

async def _go_menu_callback(update, context):
    from app.bots.funding_bot.handlers.start import _main_menu_keyboard
    query = update.callback_query
    await query.answer()
    await query.message.reply_text(
        "📋 <b>Главное меню</b>",
        parse_mode="HTML",
        reply_markup=_main_menu_keyboard(),
    )


from app.bots.funding_bot.handlers.positions import (
    build_positions_handler,
    _send_symbol_detail,
)

from app.bots.funding_bot.handlers.positions import (
    build_positions_handler,
    _send_symbol_detail,
    _symbol_keyboard,
    _next_funding_countdown,
)

async def _pos_refresh_callback(update, context, engine):
    query  = update.callback_query
    symbol = query.data.split(":")[1].upper()
    await query.answer()
    await _send_symbol_detail(query.message.reply_text, symbol, engine)

async def _pos_back_callback(update, context):
    query = update.callback_query
    await query.answer()
    await query.message.reply_text(
        f"📊 <b>Funding по символу</b>\n\n"
        f"{_next_funding_countdown()}\n\n"
        "Выбери символ или введи вручную:",
        parse_mode="HTML",
        reply_markup=_symbol_keyboard(),
    )


def build_app(token: str, engine) -> Application:
    app = Application.builder().token(token).build()

    app.add_handler(build_simulate_handler(engine))
    app.add_handler(build_positions_handler(engine))

    # ✅ Работают всегда вне ConversationHandler
    app.add_handler(CallbackQueryHandler(
        lambda u, c: _pos_refresh_callback(u, c, engine),
        pattern="^pos_sym:",
    ))
    app.add_handler(CallbackQueryHandler(
        _pos_back_callback,
        pattern="^pos_back$",
    ))

    app.add_handler(CallbackQueryHandler(
        lambda u, c: save_to_profile(u, c, engine),
        pattern="^sim_save$",
    ))
    app.add_handler(CallbackQueryHandler(_noop,             pattern="^sim_saved_noop$"))
    app.add_handler(CallbackQueryHandler(_go_menu_callback, pattern="^go_menu$"))

    register_start_handlers(app, engine)
    register_pnl_handlers(app, engine)
    register_funding_handlers(app, engine)
    register_analytics_handlers(app, engine)
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
        BotCommand("simulate",  "🧮 Симуляция стратегии"),
        BotCommand("funding",   "⚡ Топ funding rate"),
        BotCommand("positions", "📊 Открытые позиции"),
        BotCommand("pnl",       "💰 PnL сводка"),
        BotCommand("stats",     "📈 Аналитика по символу"),
        BotCommand("profile",   "👤 Мои симуляции"),
        BotCommand("about",     "📚 Как работает стратегия"),
        BotCommand("help",      "❓ Помощь"),
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