# config/trading/engine/ema_pipeline.py

from trading.services.angelone_service import AngelOneService
from trading.services.data_transformer import ohlc_to_dataframe
from core.strategies.ema_crossover import ema_crossover_signal


def run_ema_pipeline(
    symbol_token: str,
    interval: str = "ONE_MINUTE",
    candle_count: int = 100,
    short_span: int = 9,
    long_span: int = 21,
) -> dict:
    """
    Full EMA crossover pipeline.

    Flow:
        1. Login to SmartAPI
        2. Fetch last N candles
        3. Convert to pandas DataFrame
        4. Compute EMAs
        5. Detect crossover
        6. Return detailed structured output
    """

    try:
        # 1️⃣ Login
        service = AngelOneService()
        service.login()

        # 2️⃣ Fetch candles
        raw_data = service.fetch_recent_candles(
            symbol_token=symbol_token,
            interval=interval,
            n=candle_count,
        )

        if not raw_data:
            return {"error": "No market data received"}

        # 3️⃣ Convert to DataFrame
        df = ohlc_to_dataframe(raw_data)

        # 4️⃣ Compute EMAs (vectorized)
        df["ema_short"] = df["close"].ewm(
            span=short_span,
            adjust=False
        ).mean()

        df["ema_long"] = df["close"].ewm(
            span=long_span,
            adjust=False
        ).mean()

        # 5️⃣ Compute diff
        df["diff"] = df["ema_short"] - df["ema_long"]

        # 6️⃣ Detect crossover using pure strategy
        signal = ema_crossover_signal(df)

        # 7️⃣ Prepare last 5 candles for debugging
        last_5 = df.tail(5).reset_index().to_dict(orient="records")

        return {
            "signal": signal,
            "timestamp": str(df.index[-1]),
            "last_close": float(df["close"].iloc[-1]),
            "ema_short": float(df["ema_short"].iloc[-1]),
            "ema_long": float(df["ema_long"].iloc[-1]),
            "diff": float(df["diff"].iloc[-1]),
            "last_5_candles": last_5,
        }

    except Exception as e:
        return {"error": str(e)}
