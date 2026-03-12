def format_top_funding(data) -> str:

    if not data:
        return "📭 <b>No funding data available</b>\n"

    lines = [
        "📊 <b>Top Funding Rates</b>\n",
        "<i>"
        "Avg rate — доход за 1 выплату на вложенный капитал\n"
        "Positive — стабильность rate (чем выше тем лучше)\n"
        "Days tracked — дней наблюдения"
        "</i>\n",
    ]

    for i, row in enumerate(data, start=1):
        symbol        = row["symbol"]
        avg_funding   = float(row["avg_funding"])
        avg_pos_ratio = float(row["avg_positive_ratio"])
        days_count    = row["days_count"]

        sign = "🟢" if avg_funding >= 0 else "🔴"

        if avg_funding >= 0.0001 and avg_pos_ratio >= 0.9:
            verdict = "⭐⭐ отличный"
        elif avg_funding >= 0.00005 and avg_pos_ratio >= 0.7:
            verdict = "⭐ привлекательный"
        elif avg_funding >= 0.00001 and avg_pos_ratio >= 0.5:
            verdict = "👀 умеренный"
        elif avg_funding < 0:
            verdict = "⚠️ отрицательный"
        else:
            verdict = "😐 слабый"

        lines.append(
            f"{i}. {sign} <b>{symbol}</b>  <i>{verdict}</i>\n"
            f"   Avg rate:  <code>{avg_funding:+.4%}</code>\n"
            f"   Positive:  <code>{avg_pos_ratio:.1%}</code>\n"
            f"   Tracked:   <code>{days_count}d</code>\n"
        )

    lines.append(
        "\n<i>💡 Для арбитража: Avg rate &gt; 0.005% и Positive &gt; 70%</i>"
    )

    return "\n".join(lines)


def format_funding_history(data, symbol) -> str:

    if not data:
        return f"📭 <b>No funding history for {symbol}</b>\n"

    lines = [f"📈 <b>Funding History — {symbol}</b>\n"]

    for row in data:
        date          = row["date"]
        mean          = float(row["funding_mean"])
        std           = float(row["funding_std"])
        pos_ratio     = float(row["positive_ratio"])

        sign = "🟢" if mean >= 0 else "🔴"

        lines.append(
            f"{sign} <code>{date}</code>\n"
            f"   Mean:     <code>{mean:+.4%}</code>\n"
            f"   Std:      <code>{std:.4%}</code>\n"
            f"   Positive: <code>{pos_ratio:.1%}</code>\n"
        )

    return "\n".join(lines)


def format_persistent_symbols(data) -> str:

    if not data:
        return "📭 <b>No persistent positive symbols found</b>\n"

    lines = ["💎 <b>Persistently Positive Funding</b>\n"]

    for i, row in enumerate(data, start=1):
        symbol        = row["symbol"]
        avg_rate      = float(row["avg_rate"])
        pos_ratio     = float(row["avg_positive_ratio"])

        lines.append(
            f"{i}. 🟢 <b>{symbol}</b>\n"
            f"   Avg rate:  <code>{avg_rate:+.4%}</code>\n"
            f"   Positive:  <code>{pos_ratio:.1%}</code>\n"
        )

    return "\n".join(lines)
