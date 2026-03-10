
def format_pnl(data) -> str:

    if not data:
        return "📭 <b>No funding data available</b>\n"
    
    open_positions = data["open_positions"]
    total_notional = float(data["total_notional"])
    price_pnl      = float(data["total_price_pnl"])
    funding_pnl    = float(data["total_funding_pnl"])
    fees           = float(data["total_fees"])
    total_pnl      = float(data["total_pnl"])
    pnl_pct        = (total_pnl / total_notional * 100) if total_notional else 0

    return (
        "📊 <b>PnL Summary</b>\n"
        "\n"
        f"Positions open:  <code>{open_positions}</code>\n"
        f"Capital used:    <code>{total_notional:,.2f} USDT</code>\n"
        "\n"
        f"💰 Price PnL:    <code>{price_pnl:+.2f} USDT</code>\n"
        f"⚡ Funding PnL:  <code>{funding_pnl:+.2f} USDT</code>\n"
        f"💸 Fees paid:    <code>{-fees:.2f} USDT</code>\n"
        "\n"
        f"📉 Total PnL:    <code>{total_pnl:+.2f} USDT ({pnl_pct:+.2f}%)</code>\n"
    
    )

'''symbol,
               notional_usdt,
               spot_entry_price, fut_entry_price,
               price_pnl_usdt,
               funding_pnl_usdt,
               fees_paid_usdt,
               total_pnl_usdt,
               '''

def format_positions(data) -> str:

    if not data:
        return "📭 <b>No funding data available</b>\n"
    
    symbol           = data["symbol"]
    notional_usdt    = float(data["notional_usdt"])
    spot_entry       = float(data["spot_entry_price"])
    fut_entry        = float(data["fut_entry_price"])
    price_pnl        = float(data["price_pnl_usdt"])
    funding_pnl      = float(data["funding_pnl_usdt"])
    fees             = float(data["fees_paid_usdt"])
    total_pnl        = float(data["total_pnl_usdt"])
    opened_at        = data["opened_at"].strftime("%Y-%m-%d %H:%M")
    pnl_pct          = (total_pnl / notional_usdt * 100) if notional_usdt else 0

    return (
        f"📌 <b>{symbol}</b>\n"
        "\n"
        f"💵 Notional:      <code>{notional_usdt:,.2f} USDT</code>\n"
        f"📈 Spot entry:    <code>{spot_entry:,.4f}</code>\n"
        f"📉 Fut entry:     <code>{fut_entry:,.4f}</code>\n"
        "\n"
        f"💰 Price PnL:     <code>{price_pnl:+.2f} USDT</code>\n"
        f"⚡ Funding PnL:   <code>{funding_pnl:+.2f} USDT</code>\n"
        f"💸 Fees paid:     <code>{-fees:.2f} USDT</code>\n"
        "\n"
        f"📊 Total PnL:     <code>{total_pnl:+.2f} USDT ({pnl_pct:+.2f}%)</code>\n"
        f"🕐 Opened:        <code>{opened_at}</code>\n"
    )

def format_cashflow(data, symbol) -> str:

    if not data:
        return f"📭 <b>No cashflow history for {symbol}</b>\n"

    lines = [f"⚡ <b>Cashflow history — {symbol}</b>\n"]

    for row in data:
        funding_time = row["funding_time"].strftime("%Y-%m-%d %H:%M")
        funding_rate = float(row["funding_rate"])
        mark_price = float(row["mark_price"])
        cashflow = float(row["cashflow_usdt"])
        cumulative = float(row["cumulative_cashflow"])

        sign = "🟢" if cashflow >= 0 else "🔴"

        lines.append(
            f"{sign} <code>{funding_time}</code>\n"
            f"   Rate:       <code>{funding_rate:+.4%}</code>\n"
            f"   Mark:       <code>{mark_price:,.2f} USDT</code>\n"
            f"   Cashflow:   <code>{cashflow:+.4f} USDT</code>\n"
            f"   Cumulative: <code>{cumulative:+.4f} USDT</code>\n"
        )

    return "\n".join(lines)
