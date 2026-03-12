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


def plot_cumulative_pnl(data, symbol: str) -> BytesIO:

    df = pd.DataFrame(data)
    if df.empty:
        return _empty_chart(f'No cashflow data for {symbol}')

    fig, ax = plt.subplots(figsize=(10, 4))
    _apply_style(fig, ax)

    x = pd.to_datetime(df['funding_time'])
    y = df['cumulative_cashflow'].astype(float)

    final_color = STYLE['green'] if y.iloc[-1] >= 0 else STYLE['red']

    ax.plot(x, y, color=final_color, linewidth=2)
    ax.fill_between(x, y, 0, where=(y >= 0), color=STYLE['green'], alpha=0.15)
    ax.fill_between(x, y, 0, where=(y <  0), color=STYLE['red'],   alpha=0.15)
    ax.axhline(0, color=STYLE['text'], linewidth=0.8, linestyle='--', alpha=0.5)

    last_val = y.iloc[-1]
    ax.annotate(
        f'{last_val:+.2f} USDT',
        xy=(x.iloc[-1], last_val),
        color=final_color, fontsize=10, fontweight='bold',
        xytext=(-60, 10), textcoords='offset points',
    )

    ax.set_title(f'Cumulative Funding PnL — {symbol}', fontsize=13, pad=12)
    ax.set_ylabel('USDT', fontsize=10)
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter('%+.2f'))
    fig.autofmt_xdate()

    return _to_image(fig)


def plot_funding_history(data, symbol: str) -> BytesIO:

    df = pd.DataFrame(data)
    if df.empty:
        return _empty_chart(f'No funding history for {symbol}')

    fig, ax = plt.subplots(figsize=(10, 4))
    _apply_style(fig, ax)

    x = pd.to_datetime(df['date'])
    y = df['funding_mean'].astype(float)
    colors = [STYLE['green'] if v >= 0 else STYLE['red'] for v in y]

    ax.bar(x, y, color=colors, alpha=0.85, width=0.7)
    ax.axhline(0, color=STYLE['text'], linewidth=0.8, linestyle='--', alpha=0.5)

    mean_val = y.mean()
    ax.axhline(
        mean_val, color=STYLE['blue'], linewidth=1.2,
        linestyle=':', label=f'Avg: {mean_val:+.4%}',
    )
    ax.legend(facecolor=STYLE['bg_axes'], labelcolor=STYLE['text'], fontsize=9)

    ax.set_title(f'Funding Rate History — {symbol} (30d)', fontsize=13, pad=12)
    ax.set_ylabel('Funding Rate', fontsize=10)
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(xmax=1, decimals=3))
    fig.autofmt_xdate()

    return _to_image(fig)


def plot_basis_history(data: list, symbol: str) -> BytesIO:
    if not data:
        return _empty_chart("No basis data")

    df = pd.DataFrame(data)
    x  = pd.to_datetime(df['ts'])
    y  = df['basis_pct'].astype(float) * 100  # в проценты

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6), gridspec_kw={'height_ratios': [3, 1]})
    _apply_style(fig, ax1)
    _apply_style(fig, ax2)

    # Верхний график — basis_pct
    ax1.plot(x, y, color=STYLE['blue'], linewidth=1.5, label='Basis %')
    ax1.fill_between(x, y, 0, where=(y >= 0), color=STYLE['green'], alpha=0.2)
    ax1.fill_between(x, y, 0, where=(y <  0), color=STYLE['red'],   alpha=0.2)
    ax1.axhline(0, color=STYLE['text'], linewidth=0.8, linestyle='--', alpha=0.5)

    # Скользящее среднее
    if len(y) > 10:
        ma = y.rolling(window=10, min_periods=1).mean()
        ax1.plot(x, ma, color=STYLE['green'], linewidth=1.2,
                 linestyle='--', alpha=0.8, label='MA(10)')

    ax1.set_title(f'Basis History — {symbol}  |  7d', fontsize=12, pad=10)
    ax1.set_ylabel('Basis %', fontsize=9)
    ax1.yaxis.set_major_formatter(mticker.FormatStrFormatter('%.3f%%'))
    ax1.legend(facecolor=STYLE['bg_axes'], labelcolor=STYLE['text'], fontsize=8)


    if 'spot_mid' in df.columns:
        sp = df['spot_mid'].astype(float)
        ax2.plot(x, sp, color=STYLE['text'], linewidth=1.0, alpha=0.7)
        ax2.set_ylabel('Spot price', fontsize=8)
        ax2.yaxis.set_major_formatter(
            mticker.FuncFormatter(lambda v, _: f'${v:,.0f}')
        )

    fig.autofmt_xdate()
    fig.tight_layout()

    return _to_image(fig)


def plot_top_funding_symbols(data) -> BytesIO:

    df = pd.DataFrame(data)
    if df.empty:
        return _empty_chart('No funding data available')

    df = df.sort_values('avg_funding', ascending=True)

    fig, ax = plt.subplots(figsize=(9, 5))
    _apply_style(fig, ax)

    colors = [STYLE['green'] if v >= 0 else STYLE['red']
              for v in df['avg_funding'].astype(float)]

    bars = ax.barh(
        df['symbol'], df['avg_funding'].astype(float),
        color=colors, alpha=0.85, height=0.6,
    )

    for bar, val in zip(bars, df['avg_funding'].astype(float)):
        offset = 0.00002 if val >= 0 else -0.00002
        ha = 'left' if val >= 0 else 'right'
        ax.text(
            val + offset, bar.get_y() + bar.get_height() / 2,
            f'{val:+.4%}', va='center', ha=ha,
            color=STYLE['text'], fontsize=8,
        )

    ax.axvline(0, color=STYLE['text'], linewidth=0.8, linestyle='--', alpha=0.5)
    ax.set_title('Top Symbols by Avg Funding Rate (30d)', fontsize=13, pad=12)
    ax.set_xlabel('Avg Funding Rate', fontsize=10)
    ax.xaxis.set_major_formatter(mticker.PercentFormatter(xmax=1, decimals=3))

    return _to_image(fig)


def plot_pnl_breakdown(data: dict) -> BytesIO:

    labels = ['Price PnL', 'Funding PnL', 'Fees (−)']
    values = [
        float(data['total_price_pnl']),
        float(data['total_funding_pnl']),
        -abs(float(data['total_fees'])),
    ]
    colors = [STYLE['green'] if v >= 0 else STYLE['red'] for v in values]

    fig, ax = plt.subplots(figsize=(7, 4))
    _apply_style(fig, ax)

    bars = ax.bar(labels, values, color=colors, alpha=0.85, width=0.5)

    for bar, val in zip(bars, values):
        offset = 0.5 if val >= 0 else -0.5
        va = 'bottom' if val >= 0 else 'top'
        ax.text(
            bar.get_x() + bar.get_width() / 2, val + offset,
            f'{val:+.2f}', ha='center', va=va,
            color=STYLE['text'], fontsize=10, fontweight='bold',
        )

    total = float(data['total_pnl'])
    total_color = STYLE['green'] if total >= 0 else STYLE['red']
    ax.axhline(
        total, color=total_color, linewidth=1.5,
        linestyle='--', label=f'Total: {total:+.2f} USDT',
    )
    ax.legend(facecolor=STYLE['bg_axes'], labelcolor=STYLE['text'], fontsize=9)
    ax.axhline(0, color=STYLE['text'], linewidth=0.8, alpha=0.4)

    ax.set_title('PnL Breakdown', fontsize=13, pad=12)
    ax.set_ylabel('USDT', fontsize=10)
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter('%+.1f'))

    return _to_image(fig)