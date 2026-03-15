import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, ConversationHandler

from app.bots.funding_bot.i18n import t
from app.bots.funding_bot.utils import get_lang

logger = logging.getLogger(__name__)

STEP_RATE, STEP_POSITIVE, STEP_DAYS = range(3)

def _get_message(update):
    if update.message:
        return update.message
    if update.callback_query:
        return update.callback_query.message

def _menu_row(lang: str) -> list:
    return [InlineKeyboardButton(t(lang, "btn_menu"), callback_data="go_menu")]

def _split_message(text: str, max_len: int = 4000) -> list[str]:
    lines = text.split("\n")
    chunks = []
    current = ""
    for line in lines:
        if len(current) + len(line) + 1 > max_len:
            chunks.append(current.strip())
            current = line + "\n"
        else:
            current += line + "\n"
    if current.strip():
        chunks.append(current.strip())
    return chunks if chunks else [text]

def _rate_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    any_label = t(lang, "scr_any")
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("≥ 0.001%", callback_data="scr_rate:0.001"),
            InlineKeyboardButton("≥ 0.003%", callback_data="scr_rate:0.003"),
            InlineKeyboardButton("≥ 0.005%", callback_data="scr_rate:0.005"),
        ],
        [
            InlineKeyboardButton("≥ 0.007%", callback_data="scr_rate:0.007"),
            InlineKeyboardButton("≥ 0.010%", callback_data="scr_rate:0.010"),
            InlineKeyboardButton("≥ 0.020%", callback_data="scr_rate:0.020"),
        ],
        [
            InlineKeyboardButton("≥ 0.050%", callback_data="scr_rate:0.050"),
            InlineKeyboardButton(any_label,   callback_data="scr_rate:any"),
        ],
        _menu_row(lang),
    ])

def _positive_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    any_label  = t(lang, "scr_any")
    back_label = t(lang, "btn_back")
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("≥ 50%", callback_data="scr_pos:50"),
            InlineKeyboardButton("≥ 60%", callback_data="scr_pos:60"),
            InlineKeyboardButton("≥ 70%", callback_data="scr_pos:70"),
        ],
        [
            InlineKeyboardButton("≥ 75%", callback_data="scr_pos:75"),
            InlineKeyboardButton("≥ 80%", callback_data="scr_pos:80"),
            InlineKeyboardButton("≥ 90%", callback_data="scr_pos:90"),
        ],
        [
            InlineKeyboardButton("≥ 95%", callback_data="scr_pos:95"),
            InlineKeyboardButton(any_label, callback_data="scr_pos:any"),
        ],
        [
            InlineKeyboardButton(back_label,          callback_data="scr_back_rate"),
            InlineKeyboardButton(t(lang, "btn_menu"), callback_data="go_menu"),
        ],
    ])

def _days_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    back_label = t(lang, "btn_back")
    labels = [("3д", 3), ("7д", 7), ("14д", 14), ("30д", 30), ("60д", 60), ("90д", 90)] if lang != "en" else [("3d", 3), ("7d", 7), ("14d", 14), ("30d", 30), ("60d", 60), ("90d", 90)]
    row1 = [InlineKeyboardButton(lbl, callback_data=f"scr_days:{d}") for lbl, d in labels[:3]]
    row2 = [InlineKeyboardButton(lbl, callback_data=f"scr_days:{d}") for lbl, d in labels[3:]]
    return InlineKeyboardMarkup([
        row1,
        row2,
        [
            InlineKeyboardButton(back_label,          callback_data="scr_back_pos"),
            InlineKeyboardButton(t(lang, "btn_menu"), callback_data="go_menu"),
        ],
    ])

async def screener_start(update, context):
    lang = get_lang(context, None, update.effective_user.id)
    context.user_data["scr_lang"] = lang
    msg = _get_message(update)
    if update.callback_query:
        await update.callback_query.answer()
    await msg.reply_text(
        t(lang, "scr_step1"),
        parse_mode="HTML",
        reply_markup=_rate_keyboard(lang),
    )
    return STEP_RATE

async def screener_command(update, context):
    return await screener_start(update, context)

async def screener_rate(update, context):
    query = update.callback_query
    await query.answer()
    lang  = context.user_data.get("scr_lang", context.user_data.get("lang", "ru"))
    value = query.data.split(":")[1]
    context.user_data["scr_rate"] = value
    rate_label = t(lang, "scr_any") if value == "any" else f"≥ {value}%"
    context.user_data["scr_rate_label"] = rate_label
    await query.edit_message_text(
        t(lang, "scr_step2", rate=rate_label),
        parse_mode="HTML",
        reply_markup=_positive_keyboard(lang),
    )
    return STEP_POSITIVE

async def screener_positive(update, context):
    query = update.callback_query
    await query.answer()
    lang  = context.user_data.get("scr_lang", context.user_data.get("lang", "ru"))
    value = query.data.split(":")[1]
    context.user_data["scr_pos"] = value
    pos_label = t(lang, "scr_any") if value == "any" else f"≥ {value}%"
    context.user_data["scr_pos_label"] = pos_label
    await query.edit_message_text(
        t(lang, "scr_step3", rate=context.user_data["scr_rate_label"], pos=pos_label),
        parse_mode="HTML",
        reply_markup=_days_keyboard(lang),
    )
    return STEP_DAYS

async def screener_days(update, context, engine):
    query = update.callback_query
    await query.answer()
    lang       = context.user_data.get("scr_lang", context.user_data.get("lang", "ru"))
    days       = int(query.data.split(":")[1])
    rate       = context.user_data["scr_rate"]
    positive   = context.user_data["scr_pos"]
    rate_label = context.user_data["scr_rate_label"]
    pos_label  = context.user_data["scr_pos_label"]
    await query.edit_message_text(
        t(lang, "scr_searching", rate=rate_label, pos=pos_label, days=days),
        parse_mode="HTML",
    )
    try:
        results = _run_screener_query(engine, rate, positive, days)
    except Exception as e:
        logger.error(f"[screener] query failed: {e}")
        await query.message.reply_text(
            "❌ Ошибка при выполнении скринера." if lang == "ru" else "❌ Screener query failed.",
            parse_mode="HTML",
        )
        return ConversationHandler.END
    text_msg = _format_results(results, rate_label, pos_label, days, lang)
    chunks   = _split_message(text_msg)
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton(t(lang, "scr_new"),  callback_data="scr_restart"),
                                      InlineKeyboardButton(t(lang, "btn_menu"), callback_data="go_menu")]])
    for chunk in chunks[:-1]:
        await query.message.reply_text(chunk, parse_mode="HTML")
    await query.message.reply_text(chunks[-1], parse_mode="HTML", reply_markup=keyboard)
    return ConversationHandler.END

def _run_screener_query(engine, min_rate: str, min_positive: str, days: int):
    from sqlalchemy import text
    min_rate_val     = 0.0 if min_rate == "any" else float(min_rate) / 100
    min_positive_val = 0.0 if min_positive == "any" else float(min_positive) / 100
    sql = text("""
        SELECT
            symbol,
            AVG(funding_mean)                          AS avg_rate,
            AVG(positive_ratio)                        AS positive_ratio,
            MAX(funding_max)                           AS max_rate,
            MIN(funding_min)                           AS min_rate,
            AVG(funding_std)                           AS avg_std,
            SUM(intervals_count)                       AS total_intervals,
            COUNT(DISTINCT day)                        AS days_tracked,
            AVG(funding_mean) * 3 * 365 * 100          AS annual_yield_pct
        FROM funding_stats_daily
        WHERE day >= CURRENT_DATE - (:days * interval '1 day')
        GROUP BY symbol
        HAVING AVG(funding_mean) >= :min_rate AND AVG(positive_ratio) >= :min_positive
        ORDER BY AVG(funding_mean) DESC
        LIMIT 30
    """)
    with engine.connect() as conn:
        return conn.execute(sql, {"days": days, "min_rate": min_rate_val, "min_positive": min_positive_val}).mappings().all()

def _format_results(results, rate_label: str, pos_label: str, days: int, lang: str) -> str:
    if not results:
        return t(lang, "scr_no_results")
    day_label = f"{days}d" if lang == "en" else f"{days}д"
    header = t(lang, "scr_results_header", rate=rate_label, pos=pos_label, days=day_label, count=len(results))
    lines = [header, ""]
    for i, row in enumerate(results, start=1):
        symbol       = row["symbol"]
        avg_rate     = float(row["avg_rate"])
        positive     = float(row["positive_ratio"])
        max_rate     = float(row["max_rate"])
        min_rate     = float(row["min_rate"] or 0)
        avg_std      = float(row["avg_std"]  or 0)
        annual       = float(row["annual_yield_pct"])
        days_tracked = row["days_tracked"]
        if avg_rate >= 0.0001 and positive >= 0.9:
            verdict = t(lang, "scr_verdict_top")
        elif avg_rate >= 0.00005 and positive >= 0.7:
            verdict = t(lang, "scr_verdict_good")
        else:
            verdict = t(lang, "scr_verdict_moderate")
        stability = "🟢" if avg_std < 0.00005 else "🟡" if avg_std < 0.0002 else "🔴"
        rate_sign = "🟢" if avg_rate >= 0 else "🔴"
        if lang == "en":
            lines.append(f"<b>{i}. {symbol}</b>  <i>{verdict}</i>\n"
                         f"   {rate_sign} Avg rate:  <code>{avg_rate * 100:+.4f}%</code>  "
                         f"<i>(~{annual:.1f}% APR)</i>\n"
                         f"   📊 Positive:  <code>{positive * 100:.1f}%</code>  "
                         f"{stability} Volatility: <code>{avg_std * 100:.4f}%</code>\n"
                         f"   📈 Max: <code>{max_rate * 100:+.4f}%</code>  "
                         f"   📉 Min: <code>{min_rate * 100:+.4f}%</code>  "
                         f"   📅 <code>{days_tracked}d</code>")
        else:
            lines.append(f"<b>{i}. {symbol}</b>  <i>{verdict}</i>\n"
                         f"   {rate_sign} Avg rate:  <code>{avg_rate * 100:+.4f}%</code>  "
                         f"<i>(~{annual:.1f}% годовых)</i>\n"
                         f"   📊 Positive:  <code>{positive * 100:.1f}%</code>  "
                         f"{stability} Волат.: <code>{avg_std * 100:.4f}%</code>\n"
                         f"   📈 Max: <code>{max_rate * 100:+.4f}%</code>  "
                         f"   📉 Min: <code>{min_rate * 100:+.4f}%</code>  "
                         f"   📅 <code>{days_tracked}д</code>")
        lines.append("")
    lines.append(t(lang, "scr_hint"))
    return "\n".join(lines)

async def scr_back_to_rate(update, context):
    query = update.callback_query
    await query.answer()
    lang = context.user_data.get("scr_lang", context.user_data.get("lang", "ru"))
    await query.message.reply_text(t(lang, "scr_step1"), parse_mode="HTML", reply_markup=_rate_keyboard(lang))
    return STEP_RATE

async def scr_back_to_positive(update, context):
    query = update.callback_query
    await query.answer()
    lang       = context.user_data.get("scr_lang", context.user_data.get("lang", "ru"))
    rate_label = context.user_data.get("scr_rate_label", t(lang, "scr_any"))
    await query.message.reply_text(t(lang, "scr_step2", rate=rate_label), parse_mode="HTML", reply_markup=_positive_keyboard(lang))
    return STEP_POSITIVE

def build_screener_handler(engine) -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            CommandHandler("screener", screener_start),
            CallbackQueryHandler(screener_start, pattern="^menu_screener$"),
            CallbackQueryHandler(screener_start, pattern="^scr_restart$"),
        ],
        states={
            STEP_RATE: [CallbackQueryHandler(screener_rate, pattern="^scr_rate:")],
            STEP_POSITIVE: [
                CallbackQueryHandler(screener_positive, pattern="^scr_pos:"),
                CallbackQueryHandler(scr_back_to_rate,  pattern="^scr_back_rate$"),
            ],
            STEP_DAYS: [
                CallbackQueryHandler(lambda u, c: screener_days(u, c, engine), pattern="^scr_days:"),
                CallbackQueryHandler(scr_back_to_positive, pattern="^scr_back_pos$"),
            ],
        },
        fallbacks=[],
        per_user=True,
        per_chat=True,
        allow_reentry=True,
    )