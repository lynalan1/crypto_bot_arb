import logging
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from app.bots.funding_bot.utils import with_menu_button
from app.bots.funding_bot.queries.positions import get_total_pnl_summary
from app.bots.funding_bot.formatters.positions_fmt import format_pnl
from app.bots.funding_bot.formatters.analytics_fmt import plot_pnl_breakdown

logger = logging.getLogger(__name__)


async def pnl_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    engine,
) -> None:

    if update.message:
        reply_text  = update.message.reply_text
        reply_photo = update.message.reply_photo
    else:
        query = update.callback_query
        await query.answer()
        reply_text  = query.message.reply_text
        reply_photo = query.message.reply_photo

    try:
        summary = get_total_pnl_summary(engine)
    except Exception as e:
        logger.error(f"[pnl] failed: {e}")
        await reply_text("❌ Ошибка при загрузке PnL.", parse_mode="HTML")
        return

    if not summary or summary["open_positions"] == 0:
        await reply_text(
            "📭 <b>No open positions</b>\n\nНет данных для PnL.",
            parse_mode="HTML",
            reply_markup=with_menu_button([]))
        return

    await reply_text(format_pnl(summary), parse_mode="HTML")

    buf = plot_pnl_breakdown(summary)
    await reply_photo(photo=buf)

    logger.info("[pnl] sent summary")


def register_pnl_handlers(app, engine) -> None:
    app.add_handler(CommandHandler(
        "pnl",
        lambda u, c: pnl_command(u, c, engine),
    ))