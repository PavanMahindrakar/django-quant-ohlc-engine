# Django Quant OHLC Engine

A production-oriented, research-grade Django trading pipeline that fetches real market OHLC data from Angel One SmartAPI, transforms it using pandas, applies a vectorized EMA crossover strategy, and generates live trading signals — without placing real orders.

This project demonstrates how clean backend architecture + quantitative logic + real broker integration can be combined into a safe, demo-ready trading system.

---

## Overview

Traditional demo trading apps either:

* Hardcode dummy data, or
* Mix strategy logic directly inside views, or
* Directly place live orders (risky for demos)

This project implements a structured pipeline:

```
DB → SmartAPI Login → Real OHLC → Pandas DataFrame → EMA Strategy → Signal
```

The system is:

* Strategy-isolated
* Service-layer driven
* Vectorized (no loops)
* Safe (no order placement)
* Debug-transparent

---

## Architecture

```
config/
│
├── trading/
│   ├── engine/
│   │   └── ema_pipeline.py
│   ├── services/
│   │   ├── angelone_service.py
│   │   └── data_transformer.py
│   ├── models.py
│   ├── views.py
│   └── templates/
│
├── core/
│   └── strategies/
│       └── ema_crossover.py
```

### Design Principles

* Strategy logic is independent from Django
* Broker integration isolated in service layer
* Single SmartAPI login per request
* Vectorized pandas computation
* Debug-friendly structured output
* No real order execution

---

## Features

| Feature                   | Description                                            |
| ------------------------- | ------------------------------------------------------ |
| Real SmartAPI Login       | Authenticates using environment variables              |
| Configurable Candle Fetch | Fetch last N candles dynamically                       |
| Clean Data Transformation | Converts raw broker JSON to timezone-aware DataFrame   |
| Vectorized EMA            | Uses pandas `.ewm()` (no loops)                        |
| Event-Based Crossover     | Uses `shift()` for accurate signal detection           |
| Structured Output         | Returns signal + EMA + diff + recent candles           |
| Live UI                   | `/stocks/signals/` renders real-time signals           |
| JSON Debug API            | `/stocks/api/signals/<token>/` returns full debug info |
| Safe Demo Mode            | No order placement                                     |

---

## Strategy Logic

### EMA Crossover (Trend-Following)

Short EMA: 9
Long EMA: 21

We compute:

```python
diff = ema_short - ema_long
```

Signal Rules:

| Condition                  | Signal |
| -------------------------- | ------ |
| prev_diff < 0 and diff > 0 | BUY    |
| prev_diff > 0 and diff < 0 | SELL   |
| Otherwise                  | NONE   |

Uses pandas `shift()` to detect crossover events.

This is an **event-based strategy**, meaning it triggers only at crossover moments — not continuously while trend persists.

---

## Execution Flow

### 1️⃣ SmartAPI Login

* Reads credentials from environment
* Generates session
* Prevents repeated login per stock

### 2️⃣ Fetch OHLC Data

* Fetches last N candles
* Interval configurable (e.g., ONE_MINUTE)

### 3️⃣ Data Transformation

* Converts to pandas DataFrame
* Proper column names
* Converts to float
* Sets timezone-aware DatetimeIndex
* Sorts chronologically

### 4️⃣ EMA Computation

```python
df["ema_short"] = df["close"].ewm(span=9, adjust=False).mean()
df["ema_long"] = df["close"].ewm(span=21, adjust=False).mean()
```

Vectorized, efficient, production-style calculation.

### 5️⃣ Crossover Detection

```python
diff = df["ema_short"] - df["ema_long"]
prev_diff = diff.shift(1)
```

Generates BUY / SELL / NONE.

### 6️⃣ Structured Output

Returns:

```json
{
  "signal": "SELL",
  "timestamp": "2026-02-12 15:29:00+05:30",
  "last_close": 1192.0,
  "ema_short": 1192.29,
  "ema_long": 1192.30,
  "diff": -0.0042,
  "last_5_candles": [...]
}
```

---

## Environment Configuration

Create a `.env` file:

```
DEBUG=True

SMARTAPI_API_KEY=your_api_key
SMARTAPI_CLIENT_ID=your_client_id
SMARTAPI_USERNAME=your_username
SMARTAPI_PASSWORD=your_password
SMARTAPI_TOTP_SECRET=your_totp_secret
```

⚠ Never commit `.env` to Git.

---

## Installation

### Clone Repository

```
git clone https://github.com/PavanMahindrakar/django-quant-ohlc-engine.git
cd django-quant-ohlc-engine
```

### Create Virtual Environment

```
python -m venv venv
venv\Scripts\activate
```

### Install Dependencies

```
pip install -r requirements.txt
```

### Run Migrations

```
python manage.py migrate
```

### Start Server

```
python manage.py runserver
```

---

## Available Endpoints

### Stock Management UI

```
/stocks/
```

### Live Signal UI

```
/stocks/signals/
```

### Debug API

```
/stocks/api/signals/<symbol_token>/
```

---

## What This Project Demonstrates

✔ Real broker API integration
✔ Environment-based credential management
✔ Clean service-layer architecture
✔ Vectorized quantitative computation
✔ Event-driven crossover logic
✔ Django + Quant separation of concerns
✔ Debug transparency for demos
✔ Safe trading system design (no live orders)

---

## Safety Measures

* No order placement implemented
* Structured error handling
* Debug endpoint for transparency
* Credentials isolated in environment


---

## Tech Stack

* Python 3.10+
* Django 5
* Pandas
* NumPy
* Angel One SmartAPI

---

## Author

**Pavan Mahindrakar**
Backend & AI/ML Enthusiast

---

If you found this project useful, consider giving it a ⭐ on GitHub.
