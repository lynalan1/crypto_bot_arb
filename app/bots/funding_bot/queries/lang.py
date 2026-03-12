from sqlalchemy import text


def get_user_lang(engine, telegram_id: int) -> str:
    try:
        with engine.connect() as conn:
            row = conn.execute(text(
                "SELECT language FROM bot_users WHERE telegram_id = :tid"
            ), {"tid": telegram_id}).mappings().first()
        return row["language"] if row else "ru"
    except Exception:
        return "ru"


def set_user_lang(engine, telegram_id: int, lang: str) -> None:
    with engine.connect() as conn:
        conn.execute(text("""
            INSERT INTO bot_users (telegram_id, language)
            VALUES (:tid, :lang)
            ON CONFLICT (telegram_id) DO UPDATE SET language = :lang
        """), {"tid": telegram_id, "lang": lang})
        conn.commit()