def format_top_funding(data) -> str:

    if not data:
        return "📭 <b>No funding data available</b>\n"

    lines = ["📊 <b>Top Funding Rates</b>\n"]

    for i, row in enumerate(data, start=1):
        symbol            = row["symbol"]
        avg_funding       = float(row["avg_funding"])
        avg_pos_ratio     = float(row["avg_positive_ratio"])
        days_count        = row["days_count"]

        sign = "🟢" if avg_funding >= 0 else "🔴"

        lines.append(
            f"{i}. {sign} <b>{symbol}</b>\n"
            f"   Avg rate:     <code>{avg_funding:+.4%}</code>\n"
            f"   Positive:     <code>{avg_pos_ratio:.1%}</code>\n"
            f"   Days tracked: <code>{days_count}</code>\n"
        )

    return "\n".join(lines)


def format_funding_anomalies(data) -> str:

    if not data:
        return "✅ <b>No funding anomalies detected</b>\n"

    lines = ["🚨 <b>Funding Anomalies</b>\n"]

    for row in data:
        symbol       = row["symbol"]
        funding_rate = float(row["funding_rate"])
        funding_time = row["funding_time"].strftime("%Y-%m-%d %H:%M")

        sign = "🟢" if funding_rate >= 0 else "🔴"

        lines.append(
            f"{sign} <b>{symbol}</b>\n"
            f"   Rate:  <code>{funding_rate:+.4%}</code>\n"
            f"   Time:  <code>{funding_time}</code>\n"
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
