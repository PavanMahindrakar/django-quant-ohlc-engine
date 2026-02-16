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

    Returns structured result including:
    - Signal
    - Latest EMA values
    - EMA diff
    - Last 50 candles (chart-ready)
    - Crossover flag per candle
    """

    try:
        # -------------------------------------------------
        # 1️⃣ Fetch OHLC data
        # -------------------------------------------------
        raw_data = service.fetch_recent_candles(
            symbol_token=symbol_token,
            interval=interval,
            n=candle_count,
        )

        if not raw_data:
            return {"error": "No market data received"}

        # -------------------------------------------------
        # 2️⃣ Convert to DataFrame
        # -------------------------------------------------
        df = ohlc_to_dataframe(raw_data)

        # -------------------------------------------------
        # 3️⃣ Compute EMAs
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
        # 4️⃣ EMA difference
        # -------------------------------------------------
        df["diff"] = df["ema_short"] - df["ema_long"]

        # -------------------------------------------------
        # 5️⃣ Detect crossover points
        # -------------------------------------------------
        df["crossover"] = (
            ((df["diff"] > 0) & (df["diff"].shift(1) <= 0)) |
            ((df["diff"] < 0) & (df["diff"].shift(1) >= 0))
        )

        # -------------------------------------------------
        # 6️⃣ Strategy signal
        # -------------------------------------------------
        signal = ema_crossover_signal(df)

        # -------------------------------------------------
        # 7️⃣ Prepare last 50 candles for chart
        # -------------------------------------------------
        chart_df = df.tail(50).copy().reset_index()
        chart_df["timestamp"] = chart_df["timestamp"].astype(str)

        candles = chart_df.to_dict(orient="records")

        # -------------------------------------------------
        # 8️⃣ Return structured result
        # -------------------------------------------------
        return {
            "signal": signal,
            "timestamp": str(df.index[-1]),
            "last_close": float(df["close"].iloc[-1]),
            "ema_short": float(df["ema_short"].iloc[-1]),
            "ema_long": float(df["ema_long"].iloc[-1]),
            "diff": float(df["diff"].iloc[-1]),
            "candles": candles,
            "ohlc_count": len(raw_data),
            "df_shape": df.shape,
            "df_columns": list(df.columns),
        }

    except Exception as e:
        return {"error": str(e)}
