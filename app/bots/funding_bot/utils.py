from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def menu_button_row() -> list:
    """Строка с кнопкой меню — добавляется в любую клавиатуру."""
    return [InlineKeyboardButton("🏠 Главное меню", callback_data="go_menu")]


def with_menu_button(rows: list, lang: str = "ru") -> InlineKeyboardMarkup:
    from app.bots.funding_bot.i18n import t
    return InlineKeyboardMarkup(rows + [[
        InlineKeyboardButton(t(lang, "btn_menu"), callback_data="go_menu")
    ]])

def get_reply_funcs(update):
    if update.message:
        return (
            update.message.reply_text,
            update.message.reply_photo,
            update.message.from_user.id,
        )
    query = update.callback_query
    return (
        query.message.reply_text,
        query.message.reply_photo,
        query.from_user.id,
    )

def get_lang(context, engine, telegram_id: int) -> str:
    """Язык из кэша user_data или из БД."""
    if "lang" not in context.user_data:
        from app.bots.funding_bot.queries.lang import get_user_lang
        context.user_data["lang"] = get_user_lang(engine, telegram_id)
    return context.user_data["lang"]