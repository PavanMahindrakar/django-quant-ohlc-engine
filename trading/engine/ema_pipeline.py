# config/trading/engine/ema_pipeline.py
"""
EMA Pipeline Engine
-------------------

This module orchestrates the complete EMA trading flow:

    SmartAPI Session → Fetch OHLC → DataFrame → Indicators → Strategy → Output

It does NOT:
- Handle session caching (delegated to service layer)
- Place orders
- Contain strategy logic

It ONLY coordinates the pipeline.
"""

from trading.services.data_transformer import ohlc_to_dataframe
from core.strategies.ema_crossover import ema_crossover_signal


def run_ema_pipeline(
    service,
    symbol_token: str,
    interval: str = "ONE_MINUTE",
    candle_count: int = 100,
    short_span: int = 9,
    long_span: int = 21,
) -> dict:
    """
    Execute full EMA crossover pipeline.

    Parameters:
    -----------
    service : AngelOneService
        Already authenticated SmartAPI service instance.
        (Login should be handled outside for session reuse.)

    symbol_token : str
        SmartAPI symbol token.

    interval : str
        Candle timeframe (e.g., ONE_MINUTE).

    candle_count : int
        Number of recent candles to fetch.

    short_span : int
        Short EMA window.

    long_span : int
        Long EMA window.

    Returns:
    --------
    dict
        {
            "signal": "BUY" | "SELL" | "NONE",
            "timestamp": str,
            "last_close": float,
            "ema_short": float,
            "ema_long": float,
            "diff": float,
            "last_5_candles": list[dict]
        }
    """

    try:
        # -------------------------------------------------
        # 1️⃣ Fetch OHLC data (service must be logged in)
        # -------------------------------------------------
        raw_data = service.fetch_recent_candles(
            symbol_token=symbol_token,
            interval=interval,
            n=candle_count,
        )

        if not raw_data:
            return {"error": "No market data received"}

        # -------------------------------------------------
        # 2️⃣ Convert raw data to pandas DataFrame
        # -------------------------------------------------
        df = ohlc_to_dataframe(raw_data)

        # -------------------------------------------------
        # 3️⃣ Compute EMA indicators (vectorized)
        # -------------------------------------------------
        df["ema_short"] = df["close"].ewm(
            span=short_span,
            adjust=False
        ).mean()

        df["ema_long"] = df["close"].ewm(
            span=long_span,
            adjust=False
        ).mean()

        # -------------------------------------------------
        # 4️⃣ Compute EMA difference
        # -------------------------------------------------
        df["diff"] = df["ema_short"] - df["ema_long"]

        # -------------------------------------------------
        # 5️⃣ Apply pure strategy logic
        # -------------------------------------------------
        signal = ema_crossover_signal(df)

        # -------------------------------------------------
        # 6️⃣ Prepare debug-friendly output
        # Convert timestamps to string for JSON safety
        # -------------------------------------------------
        # chart_df = df.tail(5).copy()
        chart_df = df.tail(50).copy().reset_index()
        chart_df["timestamp"] = chart_df["timestamp"].astype(str)

        candles = chart_df.to_dict(orient="records")
        # -------------------------------------------------
        # 7️⃣ Return structured result
        # -------------------------------------------------
        return {
            "signal": signal,
            "timestamp": str(df.index[-1]),
            "last_close": float(df["close"].iloc[-1]),
            "ema_short": float(df["ema_short"].iloc[-1]),
            "ema_long": float(df["ema_long"].iloc[-1]),
            "diff": float(df["diff"].iloc[-1]),
            "candles": candles,
        }

    except Exception as e:
        return {"error": str(e)}
