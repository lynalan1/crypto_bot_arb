import logging
from telegram.ext import CommandHandler
from datetime import datetime, timezone, timedelta
from app.bots.funding_bot.queries.funding_stats import get_top_funding_symbols
from app.bots.funding_bot.formatters.funding_fmt import format_top_funding
from app.bots.funding_bot.formatters.analytics_fmt import plot_top_funding_symbols
logger = logging.getLogger(__name__)
from app.bots.funding_bot.utils import with_menu_button


def _next_funding_time() -> str:

    now   = datetime.now(timezone.utc)
    hour  = now.hour
    
    next_hour = ((hour // 8) + 1) * 8 % 24
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
        f"(в {next_dt.strftime('%H:%M')} UTC)"
    )


async def funding_command(update, context, engine) -> None:

    if update.message:
        reply_text  = update.message.reply_text
        reply_photo = update.message.reply_photo
    else:
        query = update.callback_query
        await query.answer()
        reply_text  = query.message.reply_text
        reply_photo = query.message.reply_photo

    try:
        data = get_top_funding_symbols(engine, limit=10)
    except Exception as e:
        logger.error(f"[funding] failed: {e}")
        await reply_text("❌ Ошибка при загрузке funding данных.", parse_mode="HTML")
        return

    if not data:
        await reply_text(
            "📭 <b>No funding data</b>\n\nДанные появятся после накопления истории.",
            parse_mode="HTML",
            reply_markup=with_menu_button([]),
        )
        return

    
    header = _next_funding_time() + "\n\n"

    await reply_text(
        header + format_top_funding(data),
        parse_mode="HTML",
        reply_markup=with_menu_button([]),
    )

    buf = plot_top_funding_symbols(data)
    await reply_photo(photo=buf)

    logger.info(f"[funding] sent top {len(data)} symbols")


def register_funding_handlers(app, engine) -> None:
    app.add_handler(CommandHandler(
        "funding",
        lambda u, c: funding_command(u, c, engine),
    ))