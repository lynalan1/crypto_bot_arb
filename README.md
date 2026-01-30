
---

# 📈 Crypto Funding Arbitrage Research Platform

## 🧠 Overview

This project is a **data-driven research platform for funding-rate arbitrage strategies** on cryptocurrency exchanges (Binance).

The system:

* collects **raw market & funding data**,
* builds **aggregated analytical datasets**,
* and simulates **paper (virtual) positions** to evaluate funding arbitrage profitability **without risking real capital**.

The main focus is **spot ↔ futures funding arbitrage** and basis analysis.

---

## 🎯 Goals of the Project

* Build a **reliable data pipeline** for funding and orderbook data
* Analyze **funding behavior over time** (daily statistics)
* Track **basis (futures – spot)** dynamics
* Simulate **paper trading strategies** based on funding
* Provide a solid foundation for future:

  * backtesting
  * strategy optimization
  * live alerts / execution

---

## 🏗️ Architecture (High Level)

```text
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
```

Each layer is **decoupled** and can be tested independently.

---

## 🧩 Data Model

### 1️⃣ `symbols`

Reference table for all tradable instruments.

Used to enforce data consistency via foreign keys.

**Example fields:**

* `symbol` (BTCUSDT)
* `base_asset` (BTC)
* `quote_asset` (USDT)
* `market` (spot / futures_um)
* `is_active`

---

### 2️⃣ `funding_events`

Raw funding-rate events from Binance Futures.

Each row represents **one funding timestamp**.

**Key fields:**

* `symbol`
* `funding_time`
* `funding_rate`
* `collected_at`

Purpose:

* immutable raw data
* source of truth for all funding analytics

---

### 3️⃣ `funding_stats_daily`

Daily aggregated funding statistics per symbol.

Computed from `funding_events`.

**Metrics:**

* `intervals_count` — number of funding events in the day
* `funding_mean`
* `funding_std`
* `funding_min / funding_max`
* `positive_ratio` — share of positive funding intervals

Used to:

* analyze long-term funding behavior
* identify persistent funding bias

---

### 4️⃣ `orderbook_bbo_snapshots`

Best Bid / Best Ask snapshots for **spot and futures**.

Collected via WebSocket with time-bucketing.

**Key fields:**

* spot & futures bid/ask prices
* mid prices
* basis (absolute & %)
* timestamped snapshots

---

### 5️⃣ `basis_ohlc_1m`

1-minute aggregated basis & spread statistics.

Built from `orderbook_bbo_snapshots`.

**Metrics:**

* average / min / max basis
* average spot & futures spread
* samples count

Used for:

* volatility analysis
* liquidity & execution quality estimation

---

### 6️⃣ `paper_positions`

Virtual (paper) trading positions.

Represents **current simulated state** of a strategy.

**Examples:**

* long spot + short futures
* position size, entry price, timestamps

---

### 7️⃣ `paper_funding_cashflows`

Funding-related cashflows for paper positions.

Each row = **one funding payment event**.

Allows:

* precise PnL calculation
* cumulative funding tracking
* strategy-level performance analysis

---

## ⚙️ Tech Stack

* **Python 3.10+**
* **PostgreSQL**
* **SQLAlchemy**
* **Binance REST & WebSocket API**
* **Docker / Docker Compose**
* Async IO (`asyncio`, `websockets`)

---

## 🧪 Design Principles

* **Event-driven architecture**
* **Time-bucketed aggregation** (5s / 1m / 1d)
* **Idempotent writes** (`ON CONFLICT DO UPDATE`)
* **Separation of concerns**:

  * raw data ≠ aggregates ≠ strategy state
* **Paper trading before real capital**

---

## 🚀 How to Run (Simplified)

```bash
# 1. Start PostgreSQL
docker-compose up -d

# 2. Seed symbols
python app/core/symbols/seeder.py

# 3. Collect funding events
python app/core/funding_collector/fetch_funding.py

# 4. Build daily funding stats
python app/core/funding_stats/daily_agg.py

# 5. Start orderbook WebSocket collector
python app/core/orderbook/orderbook_ws.py
```

---

## 📊 Example Use Cases

* Identify symbols with **persistently positive funding**
* Compare **funding vs basis** dynamics
* Simulate funding-arbitrage profitability over months
* Evaluate liquidity & spread impact on execution
* Build alerts for abnormal funding/basis conditions

---

## 🧠 Why This Project Matters

This project demonstrates:

* real-world **market data engineering**
* understanding of **derivatives mechanics**
* correct handling of **time-series data**
* ability to design **research-grade trading infrastructure**

It is intentionally built as a **research & simulation platform**, not a “black-box trading bot”.

---

## 🛣️ Roadmap

* [ ] Strategy backtesting engine
* [ ] Risk metrics (drawdown, variance)
* [ ] Multi-exchange support
* [ ] Telegram / Web dashboard
* [ ] Live alerting on funding anomalies

---

## ⚠️ Disclaimer

This project is for **research and educational purposes only**.
It does **not** execute real trades or manage real funds.

---
