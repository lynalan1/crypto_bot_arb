import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pandas as pd
from io import BytesIO

STYLE = {
    'bg':      '#1a1a2e',
    'bg_axes': '#16213e',
    'green':   '#00d4aa',
    'red':     '#ff4757',
    'blue':    '#3d84ff',
    'text':    '#e0e0e0',
    'grid':    '#2a2a4a',
}


def _apply_style(fig, ax) -> None:
    fig.patch.set_facecolor(STYLE['bg'])
    ax.set_facecolor(STYLE['bg_axes'])
    ax.tick_params(colors=STYLE['text'], labelsize=9)
    ax.xaxis.label.set_color(STYLE['text'])
    ax.yaxis.label.set_color(STYLE['text'])
    ax.title.set_color(STYLE['text'])
    ax.grid(color=STYLE['grid'], linewidth=0.5, alpha=0.7)
    for spine in ax.spines.values():
        spine.set_edgecolor(STYLE['grid'])


def _to_image(fig) -> BytesIO:
    buf = BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight')
    buf.seek(0)
    plt.close(fig)
    return buf

def format_simulation_summary(summary: dict) -> str:

    symbol      = summary["symbol"]
    side        = summary["side"]
    notional    = summary["notional_usdt"]
    days        = summary["days"]
    date_from   = summary["date_from"].strftime("%d.%m.%Y")
    date_to     = summary["date_to"].strftime("%d.%m.%Y")
    intervals   = summary["intervals_count"]
    funding_pnl = summary["funding_pnl"]
    fees        = summary["fees"]
    total_pnl   = summary["total_pnl"]
    pnl_pct     = summary["total_pnl_pct"]

    side_label = (
        "🔵 Long spot / Short futures"
        if side == "SHORT"
        else "🟣 Short spot / Long futures"
    )
    total_color = "🟢" if total_pnl >= 0 else "🔴"
    entry_price = summary.get("avg_entry_price")
    entry_line  = (
        f"📌 Entry price:    <code>{entry_price:,.2f} USDT</code>\n"
        if entry_price else ""
    )

    return (
        f"📊 <b>Simulation — {symbol}</b>\n"
        f"{side_label}\n"
        "\n"
        f"📅 Period:         <code>{date_from} → {date_to} ({days}d)</code>\n"
        f"💵 Notional:       <code>{notional:,.2f} USDT</code>\n"
        f"{entry_line}"
        f"🔁 Intervals:      <code>{intervals}</code>\n"
        "\n"
        f"⚡ Funding PnL:    <code>{funding_pnl:+.2f} USDT</code>\n"
        f"💸 Fees paid:      <code>{-fees:.2f} USDT</code>\n"
        "\n"
        f"{total_color} Total PnL:      "
        f"<code>{total_pnl:+.2f} USDT ({pnl_pct:+.2f}%)</code>\n"
    )


def format_profile_summary(data: dict) -> str:

    count        = data["simulations_count"]
    notional     = float(data["total_notional"]   or 0)
    funding_pnl  = float(data["total_funding_pnl"] or 0)
    fees         = float(data["total_fees"]        or 0)
    total_pnl    = float(data["total_pnl"]         or 0)
    pnl_pct      = (total_pnl / notional * 100) if notional else 0
    total_color  = "🟢" if total_pnl >= 0 else "🔴"

    return (
        "👤 <b>Your Profile</b>\n"
        "\n"
        f"Simulations run:   <code>{count}</code>\n"
        f"Total notional:    <code>{notional:,.2f} USDT</code>\n"
        "\n"
        f"⚡ Funding PnL:    <code>{funding_pnl:+.2f} USDT</code>\n"
        f"💸 Fees paid:      <code>{-fees:.2f} USDT</code>\n"
        "\n"
        f"{total_color} Total PnL:      "
        f"<code>{total_pnl:+.2f} USDT ({pnl_pct:+.2f}%)</code>\n"
    )


def format_simulation_list(simulations) -> str:

    if not simulations:
        return "📭 <b>No simulations yet</b>\n\nUse /simulate to run your first one."

    lines = ["📋 <b>Your Simulations</b>\n"]

    for sim in simulations:
        total_pnl  = float(sim["total_pnl"])
        pnl_pct    = float(sim["total_pnl_pct"])
        notional   = float(sim["notional_usdt"])
        days       = sim["days"]
        symbol     = sim["symbol"]
        date       = sim["created_at"].strftime("%d.%m.%Y")
        sign       = "🟢" if total_pnl >= 0 else "🔴"

        lines.append(
            f"{sign} <b>{symbol}</b>  "
            f"<code>{notional:,.0f}$</code>  "
            f"<code>{total_pnl:+.2f} USDT ({pnl_pct:+.2f}%)</code>  "
            f"<code>{days}d</code>  "
            f"<i>{date}</i>"
        )

    return "\n".join(lines)


def plot_simulation(summary: dict, history: list) -> BytesIO:

    if not history:
        return _empty_chart("No simulation data")

    df = pd.DataFrame(history)
    x  = pd.to_datetime(df["funding_time"])
    y  = df["cumulative_cashflow"].astype(float)

    fees        = abs(summary["fees"])
    total_pnl   = summary["total_pnl"]
    symbol      = summary["symbol"]
    days        = summary["days"]
    final_color = STYLE['green'] if total_pnl >= 0 else STYLE['red']

    fig, ax = plt.subplots(figsize=(10, 4))
    _apply_style(fig, ax)


    ax.plot(x, y, color=STYLE['blue'], linewidth=2, label='Cumulative funding PnL')
    ax.fill_between(x, y, 0, where=(y >= 0), color=STYLE['green'], alpha=0.12)
    ax.fill_between(x, y, 0, where=(y <  0), color=STYLE['red'],   alpha=0.12)

    # Нулевая линияs
    ax.axhline(0, color=STYLE['text'], linewidth=0.8, linestyle='--', alpha=0.4)


    ax.axhline(
        fees, color=STYLE['red'], linewidth=1.2,
        linestyle=':', label=f'Fees threshold: {fees:.2f} USDT',
    )


    ax.fill_between(
        x, 0, fees,
        color=STYLE['red'], alpha=0.06,
    )

    # Аннотация последнего значения
    last_funding = y.iloc[-1]
    ax.annotate(
        f'Funding: {last_funding:+.2f}',
        xy=(x.iloc[-1], last_funding),
        color=STYLE['blue'], fontsize=9,
        xytext=(-80, 10), textcoords='offset points',
    )

    # Аннотация итогового PnL с учётом fees
    ax.annotate(
        f'Net PnL: {total_pnl:+.2f} USDT',
        xy=(x.iloc[-1], last_funding - fees),
        color=final_color, fontsize=10, fontweight='bold',
        xytext=(-80, -20), textcoords='offset points',
    )

    ax.set_title(
        f'Simulation — {symbol}  |  {days}d  |  '
        f'{summary["notional_usdt"]:,.0f} USDT',
        fontsize=12, pad=12,
    )
    ax.set_ylabel('USDT', fontsize=10)
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter('%+.2f'))
    ax.legend(facecolor=STYLE['bg_axes'], labelcolor=STYLE['text'], fontsize=9)
    fig.autofmt_xdate()

    return _to_image(fig)


def _empty_chart(message: str) -> BytesIO:
    fig, ax = plt.subplots(figsize=(6, 3))
    _apply_style(fig, ax)
    ax.text(
        0.5, 0.5, f'📭 {message}',
        ha='center', va='center',
        color=STYLE['text'], fontsize=12,
        transform=ax.transAxes,
    )
    ax.set_axis_off()
    return _to_image(fig)
