# 🤖 Funding Rate Arbitrage Bot

Telegram bot for **funding rate arbitrage research** on Binance.  
Screener, PnL simulation, basis analytics — across 80+ symbols.

**Live demo → [@arbengin_bot](https://t.me/arbengin_bot)**

---

## 💡 What is Funding Rate Arbitrage?

Every 8 hours Binance charges a fee between longs and shorts on futures — called the **funding rate**.

**The strategy:**
- Open **Long spot** + **Short futures** on the same asset simultaneously
- Price goes up → spot gains, futures loses → **net: 0**
- Price goes down → spot loses, futures gains → **net: 0**
- Every 8 hours → short receives funding payment ✅

Market direction doesn't matter. You just collect the funding.

---

## ✨ Features

| Feature | Description |
|---|---|
| 🔍 **Screener** | Top symbols ranked by yield and stability |
| ⏰ **Funding Timer** | Countdown to next payment per symbol |
| 🧮 **Simulation** | PnL calculation on real historical data with fees |
| 📈 **Basis Analytics** | Futures vs spot spread dynamics |
| 👤 **Profile** | Save and track your simulations |
| 🌐 **i18n** | Russian and English language support |

---

## 🏗️ Architecture

```
Binance API / WebSocket
        ↓
 Raw Events Layer
 (funding_events, orderbook_bbo_snapshots)
        ↓
 Aggregation Layer
 (funding_stats_daily, basis_ohlc_1m)
        ↓
 Simulation Layer
 (paper_positions, paper_funding_cashflows)
        ↓
 Telegram Bot
 (screener, simulate, analytics, profile)
```

---

## 🗂️ Project Structure

```
app/
├── core/
│   ├── funding_collector/         # Binance funding events collector
│   │   ├── funding_events.py      # Raw WebSocket collector
│   │   └── funding_stats_daily.py # Daily aggregation
│   ├── orderbook_bbo_snapshots/   # BBO snapshots via WebSocket
│   ├── premium_index_snapshots/   # Premium index data
│   ├── paper_trading/             # Virtual positions & cashflows
│   ├── symbols/                   # Symbol seeder
│   └── runner.py                  # Core services runner
│
└── bots/
    └── funding_bot/
        ├── handlers/              # Telegram command handlers
        │   ├── start.py           # /start, /menu, /help, /about
        │   ├── positions.py       # /positions — funding timer per symbol
        │   ├── funding.py         # /funding — top symbols
        │   ├── screener.py        # /screener — filter by criteria
        │   ├── simulate.py        # /simulate — PnL simulation
        │   ├── analytics.py       # /stats — basis analytics
        │   └── profile.py         # /profile — saved simulations
        ├── formatters/            # Message formatters & charts
        ├── queries/               # DB queries
        ├── i18n.py                # RU/EN translations
        ├── utils.py               # Helpers
        └── bot.py                 # App builder & polling
```

---

## ⚙️ Tech Stack

- **Python 3.10+**
- **PostgreSQL**
- **SQLAlchemy** (sync, Core)
- **python-telegram-bot 20+** (async)
- **Binance REST & WebSocket API**
- **Matplotlib** — charts
- **Docker / Docker Compose**

---

## 🚀 Setup

### 1. Clone

```bash
git clone https://github.com/lynalan1/funding-arb-bot
cd funding-arb-bot
```

### 2. Create virtual environment

```bash
python -m venv .venv
source .venv/bin/activate        # Linux/macOS
.venv\Scripts\activate           # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment

Create `.env` in the project root:

```env
# Telegram
TELEGRAM_TOKEN=your_bot_token_here

# PostgreSQL
DB_HOST=localhost
DB_PORT=5432
DB_NAME=funding_arb
DB_USER=postgres
DB_PASSWORD=your_password_here

# Binance (read-only, no trading required)
BINANCE_API_KEY=your_api_key
BINANCE_API_SECRET=your_api_secret
```

### 5. Start PostgreSQL

```bash
docker-compose up -d
```

### 6. Seed symbols

```bash
python app/core/symbols/seeder.py
```

### 7. Start data collectors

```bash
# Collect raw funding events from Binance
python app/core/funding_collector/funding_events.py

# Build daily funding stats
python app/core/funding_collector/funding_stats_daily.py

# Start orderbook WebSocket collector
python app/core/orderbook_bbo_snapshots/order_book.py
```

### 8. Run the bot

```bash
python main.py
```

---

## 🗄️ Database Schema (key tables)

```sql
CREATE TABLE bot_users (
    telegram_id BIGINT PRIMARY KEY,
    username    TEXT,
    language    VARCHAR(2) DEFAULT 'ru',
    created_at  TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE funding_events (
    id           SERIAL PRIMARY KEY,
    symbol       TEXT NOT NULL,
    funding_rate NUMERIC NOT NULL,
    funding_time TIMESTAMPTZ NOT NULL,
    collected_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE funding_stats_daily (
    symbol          TEXT NOT NULL,
    day             DATE NOT NULL,
    intervals_count INTEGER,
    funding_mean    NUMERIC,
    funding_std     NUMERIC,
    funding_min     NUMERIC,
    funding_max     NUMERIC,
    positive_ratio  NUMERIC,
    PRIMARY KEY (symbol, day)
);

CREATE TABLE user_simulations (
    id              SERIAL PRIMARY KEY,
    telegram_id     BIGINT REFERENCES bot_users(telegram_id),
    symbol          TEXT,
    side            TEXT,
    notional_usdt   NUMERIC,
    date_from       TIMESTAMPTZ,
    date_to         TIMESTAMPTZ,
    days            INTEGER,
    funding_pnl     NUMERIC,
    fees            NUMERIC,
    total_pnl       NUMERIC,
    total_pnl_pct   NUMERIC,
    intervals_count INTEGER,
    created_at      TIMESTAMPTZ DEFAULT now()
);
```

---

## 📊 Bot Commands

| Command | Description |
|---|---|
| `/start` | Start the bot, choose language |
| `/menu` | Main menu |
| `/funding` | Top 10 symbols by funding rate |
| `/positions` | Funding timer & stats per symbol |
| `/screener` | Filter symbols by rate / stability / period |
| `/simulate` | Simulate PnL on historical data |
| `/stats` | Basis and spread analytics |
| `/profile` | Your saved simulations |
| `/about` | How the strategy works (5 pages) |
| `/help` | All commands |

---

## ⚠️ Disclaimer

This project is for **research and educational purposes only**.  
It does **not** execute real trades or manage real funds.  
Always do your own research before trading.

---

Live bot: [@arbengin_bot](https://t.me/arbengin_bot)