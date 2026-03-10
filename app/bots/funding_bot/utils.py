from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def menu_button_row() -> list:
    """Строка с кнопкой меню — добавляется в любую клавиатуру."""
    return [InlineKeyboardButton("🏠 Главное меню", callback_data="go_menu")]


def with_menu_button(rows: list) -> InlineKeyboardMarkup:
    """Оборачивает список кнопок добавляя строку меню снизу."""
    return InlineKeyboardMarkup(rows + [menu_button_row()])


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