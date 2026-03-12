# app/bots/funding_bot/i18n.py

STRINGS = {
    "ru": {
        # --- Меню ---
        "main_menu":            "📋 <b>Главное меню</b>",
        "btn_positions":        "⏰ Следующая выплата",
        "btn_screener":         "🔍 Скринер",
        "btn_funding":          "📊 Топ символов",
        "btn_analytics":        "📈 Аналитика",
        "btn_simulate":         "🧮 Симуляция",
        "btn_profile":          "👤 Профиль",
        "btn_about":            "📚 Как это работает",
        "btn_menu":             "🏠 Главное меню",
        "btn_back":             "◀️ Назад",
        "btn_refresh":          "🔄 Обновить",
        "btn_manual_input":     "✏️ Ввести вручную",
        "btn_to_list":          "◀️ К списку",
        "btn_simulate_this":    "🧮 Симулировать",

        # --- Язык ---
        "lang_choose":          "🌐 <b>Выбери язык / Choose language</b>",
        "lang_set_ru":          "✅ Язык установлен: <b>Русский 🇷🇺</b>",
        "lang_set_en":          "✅ Language set: <b>English 🇬🇧</b>",

        # --- Start ---
        "start_greeting":       "👋 <b>{name}</b>!\n\n🌐 <b>Выбери язык / Choose language</b>",

        # --- Общие ---
        "loading":              "⏳ Загружаю данные...",
        "error":                "❌ Ошибка при загрузке данных.",
        "no_data":              "📭 Нет данных.",
        "choose_symbol":        "Выбери символ или введи вручную:",
        "manual_prompt":        "✏️ <b>Введи символ</b>\n\nНапример: <code>SOLUSDT</code>, <code>solusdt</code>\n<i>Регистр не важен — формат XXXUSDT</i>",
        "invalid_symbol":       "❌ Некорректный символ.\n\nФормат: <code>BTCUSDT</code>\nПопробуй ещё раз:",
        "no_symbol_data":       "📭 Нет данных по <b>{symbol}</b>.\n\nПроверь правильность написания.",

        # --- Help ---
        "help_title":           "📖 <b>Команды бота</b>",
        "help_positions":       "⏰ /positions — текущий funding rate по символу и когда будет следующая выплата",
        "help_funding":         "📊 /funding — топ символов по среднему funding rate за 30 дней",
        "help_screener":        "🔍 /screener — найти символы по своим критериям (rate, стабильность, период)",
        "help_stats":           "📈 /stats — аналитика по символу (история rate, basis, спреды)",
        "help_simulate":        "🧮 /simulate — симуляция стратегии на исторических данных с графиком PnL",
        "help_profile":         "👤 /profile — история симуляций с итоговым PnL",
        "help_about":           "📚 /about — объяснение стратегии funding арбитража",
        "help_menu":            "📋 /menu — открыть главное меню",
        "help_cancel":          "❌ /cancel — отменить текущий диалог",

        # --- Positions ---
        "positions_title":      "📊 <b>Funding по символу</b>",
        "positions_choose":     "Выбери символ или введи вручную:",
        "positions_loading":    "⏳ Загружаю данные по <b>{symbol}</b>...",
        "next_payment":         "⏰ <b>Следующая выплата через:</b> <code>{time}</code> <i>(в {hour} UTC)</i>",
        "positions_detail":     (
            "📊 <b>Funding — {symbol}</b>\n\n"
            "{countdown}\n\n"
            "{rate_sign} <b>Текущий rate:</b>  <code>{current_rate:+.4%}</code>\n"
            "   <i>последняя выплата: {last_time}</i>\n\n"
            "📅 <b>Статистика за 30 дней:</b>\n"
            "{avg_sign} Avg rate:       <code>{avg_rate:+.4%}</code>\n"
            "   Positive:      <code>{pos_ratio:.1%}</code> интервалов\n"
            "   Max rate:      <code>{max_rate:+.4%}</code>\n"
            "   Min rate:      <code>{min_rate:+.4%}</code>\n"
            "   Интервалов:    <code>{intervals}</code>\n\n"
            "📈 <b>~{annual:.1f}% годовых</b> <i>(грубо, без fees)</i>\n"
        ),

        # --- Funding ---
        "funding_header":       (
            "📊 <b>Топ Funding Rates</b>\n\n"
            "<i>Avg rate — доход за 1 выплату на вложенный капитал\n"
            "Positive — стабильность rate (чем выше тем лучше)\n"
            "Days tracked — дней наблюдения</i>\n"
        ),
        "funding_hint":         "💡 Для арбитража: Avg rate &gt; 0.005% и Positive &gt; 70%",
        "verdict_excellent":    "⭐⭐ отличный",
        "verdict_good":         "⭐ привлекательный",
        "verdict_moderate":     "👀 умеренный",
        "verdict_negative":     "⚠️ отрицательный",
        "verdict_weak":         "😐 слабый",

        # --- Screener ---
        "scr_step1":            "🔍 <b>Скринер</b>\n\n<b>Шаг 1 из 3</b> — минимальный Avg rate:",
        "scr_step2":            "🔍 <b>Скринер</b>\n\n✅ Avg rate: <code>{rate}</code>\n\n<b>Шаг 2 из 3</b> — минимальный Positive ratio:",
        "scr_step3":            "🔍 <b>Скринер</b>\n\n✅ Avg rate: <code>{rate}</code>\n✅ Positive: <code>{pos}</code>\n\n<b>Шаг 3 из 3</b> — период:",
        "scr_searching":        "🔍 <b>Скринер</b>\n\n✅ Avg rate: <code>{rate}</code>\n✅ Positive: <code>{pos}</code>\n✅ Период: <code>{days} дней</code>\n\n⏳ Ищу символы...",
        "scr_any":              "Любой",
        "scr_new":              "🔄 Новый поиск",
        "scr_days_label":       "{days} дней",
        "scr_no_results":       "📭 Нет символов под твои критерии.\n\n<i>Попробуй снизить минимальный rate или positive ratio.</i>",
        "scr_results_header":   "🔍 <b>Скринер — результаты</b>\n\n<i>Rate {rate} | Positive {pos} | {days}д</i>\n\nНайдено: <b>{count}</b> символов\n",
        "scr_hint":             "💡 ~% годовых — грубая оценка без учёта fees",
        "scr_verdict_top":      "⭐⭐ отличный",
        "scr_verdict_good":     "⭐ хороший",
        "scr_verdict_moderate": "👀 умеренный",

        # --- Simulate ---
        "sim_choose_symbol":    "🧮 <b>Симуляция</b>\n\nВыбери символ:",
        "sim_choose_side":      "📊 <b>Simulation — {symbol}</b>\n\nВыбери сторону:",
        "sim_side_short":       "📈 Long spot / Short futures",
        "sim_side_long":        "📉 Short spot / Long futures",
        "sim_choose_amount":    "📊 <b>Simulation — {symbol}</b>\n{side}\n\nВыбери сумму или напиши свою:\n<i>от {min} до {max:,} USDT</i>",
        "sim_choose_period":    "📊 <b>Simulation — {symbol}</b>\n💵 Notional: <code>{amount:,.0f} USDT</code>\n\nВыбери период:",
        "sim_calculating":      "⏳ Считаю симуляцию для <b>{symbol}</b>...",
        "sim_no_data":          "📭 Недостаточно данных для <b>{symbol}</b>.\n\nПопробуй другой символ или период.",
        "sim_save":             "💾 Сохранить в профиль",
        "sim_saved":            "✅ Сохранено",
        "sim_new":              "🔁 Новая симуляция",
        "sim_short_label":      "🔵 Long spot / Short futures",
        "sim_long_label":       "🟣 Short spot / Long futures",
        "sim_days":             "{days}д",

        # --- Profile ---
        "profile_empty":        "👤 <b>Профиль</b>\n\n📭 У тебя ещё нет симуляций.\n\nЗапусти первую: /simulate",
        "profile_deleted":      "✅ Симуляция удалена.",
        "profile_no_more":      "👤 <b>Профиль</b>\n\n📭 Симуляций больше нет.\n\nЗапусти новую: /simulate",
        "delete_confirm":       "🗑 <b>Удалить симуляцию?</b>\n\nЭто действие нельзя отменить.",
        "btn_delete":           "🗑 Удалить",
        "btn_yes_delete":       "✅ Да, удалить",
        "btn_cancel":           "❌ Отмена",
        "btn_profile_back":     "◀️ Назад",

        # --- Analytics ---
        "analytics_title":      "📈 <b>Аналитика</b>\n\nВыбери символ или введи вручную:",
        "analytics_loading":    "⏳ Загружаю аналитику для <b>{symbol}</b>...",
        "analytics_no_data":    "📭 Нет данных по <b>{symbol}</b>.\n\nДанные накапливаются — попробуй позже.",
        "analytics_error":      "❌ Ошибка при загрузке данных.",

        # --- About pages ---
        "about_page_label":     "Страница {cur} из {total}",
        "about_p1_title":       "📚 <b>Как работает funding rate арбитраж</b>\n<i>Страница 1 из 5 — Что такое funding rate?</i>",
        "about_p2_title":       "📚 <b>Как работает funding rate арбитраж</b>\n<i>Страница 2 из 5 — Суть стратегии</i>",
        "about_p3_title":       "📚 <b>Как работает funding rate арбитраж</b>\n<i>Страница 3 из 5 — Математика</i>",
        "about_p4_title":       "📚 <b>Как работает funding rate арбитраж</b>\n<i>Страница 4 из 5 — Риски</i>",
        "about_p5_title":       "📚 <b>Как работает funding rate арбитраж</b>\n<i>Страница 5 из 5 — Словарь терминов</i>",
    },

    "en": {
        # --- Menu ---
        "main_menu":            "📋 <b>Main Menu</b>",
        "btn_positions":        "⏰ Next Payment",
        "btn_screener":         "🔍 Screener",
        "btn_funding":          "📊 Top Symbols",
        "btn_analytics":        "📈 Analytics",
        "btn_simulate":         "🧮 Simulate",
        "btn_profile":          "👤 Profile",
        "btn_about":            "📚 How it works",
        "btn_menu":             "🏠 Main Menu",
        "btn_back":             "◀️ Back",
        "btn_refresh":          "🔄 Refresh",
        "btn_manual_input":     "✏️ Type manually",
        "btn_to_list":          "◀️ Back to list",
        "btn_simulate_this":    "🧮 Simulate",

        # --- Language ---
        "lang_choose":          "🌐 <b>Выбери язык / Choose language</b>",
        "lang_set_ru":          "✅ Язык установлен: <b>Русский 🇷🇺</b>",
        "lang_set_en":          "✅ Language set: <b>English 🇬🇧</b>",

        # --- Start ---
        "start_greeting":       "👋 <b>{name}</b>!\n\n🌐 <b>Выбери язык / Choose language</b>",

        # --- Common ---
        "loading":              "⏳ Loading data...",
        "error":                "❌ Failed to load data.",
        "no_data":              "📭 No data available.",
        "choose_symbol":        "Choose a symbol or type manually:",
        "manual_prompt":        "✏️ <b>Enter symbol</b>\n\nExample: <code>SOLUSDT</code>, <code>solusdt</code>\n<i>Case insensitive — use XXXUSDT format</i>",
        "invalid_symbol":       "❌ Invalid symbol.\n\nFormat: <code>BTCUSDT</code>\nTry again:",
        "no_symbol_data":       "📭 No data for <b>{symbol}</b>.\n\nCheck the symbol name.",

        # --- Help ---
        "help_title":           "📖 <b>Bot Commands</b>",
        "help_positions":       "⏰ /positions — current funding rate for a symbol and next payment countdown",
        "help_funding":         "📊 /funding — top symbols by average funding rate over 30 days",
        "help_screener":        "🔍 /screener — filter symbols by your own criteria (rate, stability, period)",
        "help_stats":           "📈 /stats — symbol analytics (rate history, basis, spreads)",
        "help_simulate":        "🧮 /simulate — strategy simulation on historical data with PnL chart",
        "help_profile":         "👤 /profile — simulation history with total PnL",
        "help_about":           "📚 /about — explanation of funding rate arbitrage strategy",
        "help_menu":            "📋 /menu — open main menu",
        "help_cancel":          "❌ /cancel — cancel current dialog",

        # --- Positions ---
        "positions_title":      "📊 <b>Funding by Symbol</b>",
        "positions_choose":     "Choose a symbol or type manually:",
        "positions_loading":    "⏳ Loading data for <b>{symbol}</b>...",
        "next_payment":         "⏰ <b>Next payment in:</b> <code>{time}</code> <i>(at {hour} UTC)</i>",
        "positions_detail":     (
            "📊 <b>Funding — {symbol}</b>\n\n"
            "{countdown}\n\n"
            "{rate_sign} <b>Current rate:</b>  <code>{current_rate:+.4%}</code>\n"
            "   <i>last payment: {last_time}</i>\n\n"
            "📅 <b>30-day stats:</b>\n"
            "{avg_sign} Avg rate:     <code>{avg_rate:+.4%}</code>\n"
            "   Positive:    <code>{pos_ratio:.1%}</code> of intervals\n"
            "   Max rate:    <code>{max_rate:+.4%}</code>\n"
            "   Min rate:    <code>{min_rate:+.4%}</code>\n"
            "   Intervals:   <code>{intervals}</code>\n\n"
            "📈 <b>~{annual:.1f}% annual yield</b> <i>(rough, excl. fees)</i>\n"
        ),

        # --- Funding ---
        "funding_header":       (
            "📊 <b>Top Funding Rates</b>\n\n"
            "<i>Avg rate — income per payment on invested capital\n"
            "Positive — rate stability (higher is better)\n"
            "Days tracked — observation period in days</i>\n"
        ),
        "funding_hint":         "💡 For arb: Avg rate &gt; 0.005% and Positive &gt; 70%",
        "verdict_excellent":    "⭐⭐ excellent",
        "verdict_good":         "⭐ attractive",
        "verdict_moderate":     "👀 moderate",
        "verdict_negative":     "⚠️ negative",
        "verdict_weak":         "😐 weak",

        # --- Screener ---
        "scr_step1":            "🔍 <b>Screener</b>\n\n<b>Step 1 of 3</b> — minimum Avg rate:",
        "scr_step2":            "🔍 <b>Screener</b>\n\n✅ Avg rate: <code>{rate}</code>\n\n<b>Step 2 of 3</b> — minimum Positive ratio:",
        "scr_step3":            "🔍 <b>Screener</b>\n\n✅ Avg rate: <code>{rate}</code>\n✅ Positive: <code>{pos}</code>\n\n<b>Step 3 of 3</b> — period:",
        "scr_searching":        "🔍 <b>Screener</b>\n\n✅ Avg rate: <code>{rate}</code>\n✅ Positive: <code>{pos}</code>\n✅ Period: <code>{days} days</code>\n\n⏳ Searching...",
        "scr_any":              "Any",
        "scr_new":              "🔄 New search",
        "scr_days_label":       "{days} days",
        "scr_no_results":       "📭 No symbols match your criteria.\n\n<i>Try lowering the minimum rate or positive ratio.</i>",
        "scr_results_header":   "🔍 <b>Screener — results</b>\n\n<i>Rate {rate} | Positive {pos} | {days}d</i>\n\nFound: <b>{count}</b> symbols\n",
        "scr_hint":             "💡 Annual % is a rough estimate excluding fees",
        "scr_verdict_top":      "⭐⭐ excellent",
        "scr_verdict_good":     "⭐ good",
        "scr_verdict_moderate": "👀 moderate",

        # --- Simulate ---
        "sim_choose_symbol":    "🧮 <b>Simulation</b>\n\nChoose a symbol:",
        "sim_choose_side":      "📊 <b>Simulation — {symbol}</b>\n\nChoose side:",
        "sim_side_short":       "📈 Long spot / Short futures",
        "sim_side_long":        "📉 Short spot / Long futures",
        "sim_choose_amount":    "📊 <b>Simulation — {symbol}</b>\n{side}\n\nChoose amount or type your own:\n<i>from {min} to {max:,} USDT</i>",
        "sim_choose_period":    "📊 <b>Simulation — {symbol}</b>\n💵 Notional: <code>{amount:,.0f} USDT</code>\n\nChoose period:",
        "sim_calculating":      "⏳ Calculating simulation for <b>{symbol}</b>...",
        "sim_no_data":          "📭 Not enough data for <b>{symbol}</b>.\n\nTry a different symbol or period.",
        "sim_save":             "💾 Save to profile",
        "sim_saved":            "✅ Saved",
        "sim_new":              "🔁 New simulation",
        "sim_short_label":      "🔵 Long spot / Short futures",
        "sim_long_label":       "🟣 Short spot / Long futures",
        "sim_days":             "{days}d",

        # --- Profile ---
        "profile_empty":        "👤 <b>Profile</b>\n\n📭 No simulations yet.\n\nRun your first: /simulate",
        "profile_deleted":      "✅ Simulation deleted.",
        "profile_no_more":      "👤 <b>Profile</b>\n\n📭 No simulations left.\n\nRun a new one: /simulate",
        "delete_confirm":       "🗑 <b>Delete simulation?</b>\n\nThis cannot be undone.",
        "btn_delete":           "🗑 Delete",
        "btn_yes_delete":       "✅ Yes, delete",
        "btn_cancel":           "❌ Cancel",
        "btn_profile_back":     "◀️ Back",

        # --- Analytics ---
        "analytics_title":      "📈 <b>Analytics</b>\n\nChoose a symbol or type manually:",
        "analytics_loading":    "⏳ Loading analytics for <b>{symbol}</b>...",
        "analytics_no_data":    "📭 No data for <b>{symbol}</b>.\n\nData is being collected — try again later.",
        "analytics_error":      "❌ Failed to load data.",

        # --- About pages ---
        "about_page_label":     "Page {cur} of {total}",
        "about_p1_title":       "📚 <b>Funding Rate Arbitrage Explained</b>\n<i>Page 1 of 5 — What is funding rate?</i>",
        "about_p2_title":       "📚 <b>Funding Rate Arbitrage Explained</b>\n<i>Page 2 of 5 — Strategy overview</i>",
        "about_p3_title":       "📚 <b>Funding Rate Arbitrage Explained</b>\n<i>Page 3 of 5 — The math</i>",
        "about_p4_title":       "📚 <b>Funding Rate Arbitrage Explained</b>\n<i>Page 4 of 5 — Risks</i>",
        "about_p5_title":       "📚 <b>Funding Rate Arbitrage Explained</b>\n<i>Page 5 of 5 — Glossary</i>",
    },
}


def t(lang: str, key: str, **kwargs) -> str:
    text = STRINGS.get(lang, STRINGS["ru"]).get(key) \
        or STRINGS["ru"].get(key, key)
    return text.format(**kwargs) if kwargs else text