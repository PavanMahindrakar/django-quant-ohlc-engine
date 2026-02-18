"""
EMA Pipeline Engine
-------------------

This module orchestrates the complete EMA trading flow:

    SmartAPI Session
        ↓
    Fetch OHLC
        ↓
    Transform to DataFrame
        ↓
    Compute EMAs
        ↓
    Detect Fresh Crossover
        ↓
    Return Structured Signal Output

Important:
- Generates signal ONLY if crossover occurs on latest candle
- Prevents stale signal execution
- Returns debug metadata for dashboard visibility
"""

from trading.services.data_transformer import ohlc_to_dataframe
from django.conf import settings


def run_ema_pipeline(
    service,
    symbol_token: str,
    interval: str = "ONE_MINUTE",
    candle_count: int = 100,
    short_span: int = 9,
    long_span: int = 21,
) -> dict:
    """
    Execute strict EMA crossover pipeline.

    Signal Rules:
    -------------
    BUY  → Short EMA crosses above Long EMA on latest candle
    SELL → Short EMA crosses below Long EMA on latest candle
    NONE → No fresh crossover

    Returns:
    --------
    dict:
        {
            "signal": str,
            "timestamp": str,
            "last_close": float,
            "ema_short": float,
            "ema_long": float,
            "diff": float,
            "candles": list,
            "ohlc_count": int,
            "df_shape": tuple,
            "df_columns": list
        }
    """

    try:
        # -------------------------------------------------
        # 1️⃣ Fetch OHLC Data
        # -------------------------------------------------
        raw_data = service.fetch_recent_candles(
            symbol_token=symbol_token,
            interval=interval,
            n=candle_count,
        )

        if not raw_data:
            return {"error": "No market data received"}

        # -------------------------------------------------
        # 2️⃣ Transform to DataFrame
        # -------------------------------------------------
        df = ohlc_to_dataframe(raw_data)

        if len(df) < 2:
            return {"error": "Not enough candles for crossover detection"}

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
        # 4️⃣ EMA Difference
        # -------------------------------------------------
        df["diff"] = df["ema_short"] - df["ema_long"]

        # -------------------------------------------------
        # 5️⃣ Detect Crossover Points
        # -------------------------------------------------
        df["crossover"] = (
            ((df["diff"] > 0) & (df["diff"].shift(1) <= 0)) |
            ((df["diff"] < 0) & (df["diff"].shift(1) >= 0))
        )

        # # DEBUG: Check last 10 candles crossover behavior
        # print("Latest closed candle:")
        # print("Timestamp:", df.index[-2])
        # print("Diff:", df["diff"].iloc[-2])
        # print("Crossover:", df["crossover"].iloc[-2])
        # -------------------------------------------------
        # # 6️⃣ Strict Fresh Crossover Signal Logic
        # # -------------------------------------------------
        # latest_crossover = df["crossover"].iloc[-1]
        # current_diff = df["diff"].iloc[-1]
        #
        # if latest_crossover:
        #     if current_diff > 0:
        #         signal = "BUY"
        #     elif current_diff < 0:
        #         signal = "SELL"
        #     else:
        #         signal = "NONE"
        # else:
        #     signal = "NONE"

        # -------------------------------------------------
        # 6️⃣ Detect Latest Crossover In Entire Dataset
        # -------------------------------------------------

        crossover_rows = df[df["crossover"] == True]

        if not crossover_rows.empty:
            last_crossover_index = crossover_rows.index[-1]
            last_crossover_diff = df.loc[last_crossover_index, "diff"]
        else:
            last_crossover_index = None
            last_crossover_diff = None

        # -------------------------------------------------
        # 7️⃣ Strict Fresh Signal Logic (Trade only if latest candle crossed)
        # -------------------------------------------------

        signal_index = -1  # last fully closed candle

        if (
                last_crossover_index is not None and
                last_crossover_index == df.index[signal_index]
        ):
            if last_crossover_diff > 0:
                signal = "BUY"
            elif last_crossover_diff < 0:
                signal = "SELL"
            else:
                signal = "NONE"
        else:
            signal = "NONE"

        # -------------------------------------------------
        # Optional Force Signal (Testing Only)
        # -------------------------------------------------
        forced = getattr(settings, "FORCE_SIGNAL", None)

        if forced in ["BUY", "SELL"]:
            print(f"\n⚠️ FORCE SIGNAL ENABLED → {forced}")
            signal = forced

        # -------------------------------------------------
        # 7️⃣ Prepare Last 50 Candles for UI / Debug
        # -------------------------------------------------
        chart_df = df.copy().reset_index()
        chart_df["timestamp"] = chart_df["timestamp"].astype(str)
        candles = chart_df.to_dict(orient="records")

        # -------------------------------------------------
        # 8️⃣ Return Structured Output
        # -------------------------------------------------

        return {
            "signal": signal,
            "timestamp": str(df.index[signal_index]),
            "crossover_timestamp": str(last_crossover_index) if last_crossover_index else None,
            "last_close": float(df["close"].iloc[signal_index]),
            "ema_short": float(df["ema_short"].iloc[signal_index]),
            "ema_long": float(df["ema_long"].iloc[signal_index]),
            "diff": float(df["diff"].iloc[signal_index]),
            "candles": candles,
            "ohlc_count": len(raw_data),
            "df_shape": df.shape,
            "df_columns": list(df.columns),
        }

        # signal_index = -1  # use last fully closed candle
        #
        # return {
        #     "signal": signal,
        #     "timestamp": str(df.index[signal_index]),
        #     "last_close": float(df["close"].iloc[signal_index]),
        #     "ema_short": float(df["ema_short"].iloc[signal_index]),
        #     "ema_long": float(df["ema_long"].iloc[signal_index]),
        #     "diff": float(df["diff"].iloc[signal_index]),
        #     "candles": candles,
        #     "ohlc_count": len(raw_data),
        #     "df_shape": df.shape,
        #     "df_columns": list(df.columns),
        # }
    except Exception as e:
        return {"error": str(e)}







# from trading.services.data_transformer import ohlc_to_dataframe
# from core.strategies.ema_crossover import ema_crossover_signal
# from django.conf import settings
#
# def run_ema_pipeline(
#     service,
#     symbol_token: str,
#     interval: str = "ONE_MINUTE",
#     candle_count: int = 100,
#     short_span: int = 9,
#     long_span: int = 21,
# ) -> dict:
#     """
#     Execute full EMA crossover pipeline.
#
#     Returns structured result including:
#     - Signal
#     - Latest EMA values
#     - EMA diff
#     - Last 50 candles (chart-ready)
#     - Crossover flag per candle
#     """
#
#     try:
#         # -------------------------------------------------
#         # 1️⃣ Fetch OHLC data
#         # -------------------------------------------------
#         raw_data = service.fetch_recent_candles(
#             symbol_token=symbol_token,
#             interval=interval,
#             n=candle_count,
#         )
#
#         if not raw_data:
#             return {"error": "No market data received"}
#
#         # -------------------------------------------------
#         # 2️⃣ Convert to DataFrame
#         # -------------------------------------------------
#         df = ohlc_to_dataframe(raw_data)
#
#         # -------------------------------------------------
#         # 3️⃣ Compute EMAs
#         # -------------------------------------------------
#         df["ema_short"] = df["close"].ewm(
#             span=short_span,
#             adjust=False
#         ).mean()
#
#         df["ema_long"] = df["close"].ewm(
#             span=long_span,
#             adjust=False
#         ).mean()
#
#         # -------------------------------------------------
#         # 4️⃣ EMA difference
#         # -------------------------------------------------
#         df["diff"] = df["ema_short"] - df["ema_long"]
#
#         # -------------------------------------------------
#         # 5️⃣ Detect crossover points
#         # -------------------------------------------------
#         df["crossover"] = (
#             ((df["diff"] > 0) & (df["diff"].shift(1) <= 0)) |
#             ((df["diff"] < 0) & (df["diff"].shift(1) >= 0))
#         )
#
#         # # -------------------------------------------------
#         # # 6️⃣ Strategy signal
#         # # -------------------------------------------------
#         # signal = ema_crossover_signal(df)
#         # # if signal == "NO SIGNAL" and getattr(settings, "DEMO_MODE", False):
#         # #     signal = "BUY"
#
#         # -------------------------------------------------
#         # 6️⃣ Strategy signal (STRICT FRESH CROSSOVER)
#         # -------------------------------------------------
#
#         latest_crossover = df["crossover"].iloc[-1]
#         prev_diff = df["diff"].iloc[-2]
#         current_diff = df["diff"].iloc[-1]
#
#         if latest_crossover:
#             if current_diff > 0:
#                 signal = "BUY"
#             elif current_diff < 0:
#                 signal = "SELL"
#             else:
#                 signal = "NONE"
#         else:
#             signal = "NONE"
#
#         # -------------------------------------------------
#         # 7️⃣ Prepare last 50 candles for chart
#         # -------------------------------------------------
#         chart_df = df.tail(50).copy().reset_index()
#         chart_df["timestamp"] = chart_df["timestamp"].astype(str)
#
#         candles = chart_df.to_dict(orient="records")
#
#         # -------------------------------------------------
#         # 8️⃣ Return structured result
#         # -------------------------------------------------
#         return {
#             "signal": signal,
#             "timestamp": str(df.index[-1]),
#             "last_close": float(df["close"].iloc[-1]),
#             "ema_short": float(df["ema_short"].iloc[-1]),
#             "ema_long": float(df["ema_long"].iloc[-1]),
#             "diff": float(df["diff"].iloc[-1]),
#             "candles": candles,
#             "ohlc_count": len(raw_data),
#             "df_shape": df.shape,
#             "df_columns": list(df.columns),
#         }
#
#     except Exception as e:
#         return {"error": str(e)}
