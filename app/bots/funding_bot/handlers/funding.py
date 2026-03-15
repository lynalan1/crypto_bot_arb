import logging
from telegram.ext import CommandHandler
from datetime import datetime, timezone, timedelta
from app.bots.funding_bot.queries.funding_stats import get_top_funding_symbols
from app.bots.funding_bot.formatters.funding_fmt import format_top_funding
from app.bots.funding_bot.formatters.analytics_fmt import plot_top_funding_symbols
from app.bots.funding_bot.utils import with_menu_button, get_lang
from app.bots.funding_bot.i18n import t

logger = logging.getLogger(__name__)


async def funding_command(update, context, engine) -> None:
    if update.message:
        reply_text  = update.message.reply_text
        reply_photo = update.message.reply_photo
        tg_id       = update.message.from_user.id
    else:
        query = update.callback_query
        await query.answer()
        reply_text  = query.message.reply_text
        reply_photo = query.message.reply_photo
        tg_id       = query.from_user.id

    lang = get_lang(context, engine, tg_id)

    try:
        data = get_top_funding_symbols(engine, limit=10)
    except Exception as e:
        logger.error(f"[funding] failed: {e}")
        await reply_text(t(lang, "error"), parse_mode="HTML")
        return

    if not data:
        await reply_text(t(lang, "no_data"), parse_mode="HTML", reply_markup=with_menu_button([], lang))
        return

    countdown = _next_funding_time(lang)
    await reply_text(
        countdown + "\n\n" + format_top_funding(data, lang),
        parse_mode="HTML",
        reply_markup=with_menu_button([], lang),
    )

    buf = plot_top_funding_symbols(data)
    await reply_photo(photo=buf)

    logger.info(f"[funding] sent top {len(data)} symbols")


def _next_funding_time(lang: str = "ru") -> str:
    now       = datetime.now(timezone.utc)
    next_hour = ((now.hour // 8) + 1) * 8 % 24
    next_dt   = now.replace(hour=next_hour, minute=0, second=0, microsecond=0)
    if next_dt <= now:
        next_dt += timedelta(days=1)
    delta   = next_dt - now
    hours   = delta.seconds // 3600
    minutes = (delta.seconds % 3600) // 60
    seconds = delta.seconds % 60
    return t(lang, "next_payment",
             time=f"{hours:02d}:{minutes:02d}:{seconds:02d}",
             hour=next_dt.strftime('%H:%M'))


def register_funding_handlers(app, engine) -> None:
    app.add_handler(CommandHandler(
        "funding",
        lambda u, c: funding_command(u, c, engine),
    ))
    