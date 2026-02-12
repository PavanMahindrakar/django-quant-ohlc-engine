# config/core/strategies/ema_crossover.py
import pandas as pd


def ema_crossover_signal(df: pd.DataFrame) -> str:
    """
    Determine latest EMA crossover signal (trend-following).

    Rules:
    - EMA up crossover   → BUY
    - EMA down crossover → SELL
    - Otherwise          → NO SIGNAL
    """

    required_columns = {"ema_short", "ema_long"}

    if not required_columns.issubset(df.columns):
        raise ValueError("DataFrame must contain 'ema_short' and 'ema_long' columns")

    prev_short = df["ema_short"].shift(1)
    prev_long = df["ema_long"].shift(1)

    curr_short = df["ema_short"]
    curr_long = df["ema_long"]

    # EMA up crossover → BUY
    buy_condition = (prev_short < prev_long) & (curr_short > curr_long)

    # EMA down crossover → SELL
    sell_condition = (prev_short > prev_long) & (curr_short < curr_long)

    if buy_condition.iloc[-1]:
        return "BUY"
    elif sell_condition.iloc[-1]:
        return "SELL"
    else:
        return "NO SIGNAL"


# import pandas as pd
#
#
# def ema_crossover_signal(df: pd.DataFrame) -> str:
#     """
#     Pure Python EMA crossover strategy.
#
#     Parameters:
#         df (pd.DataFrame): Must contain 'ema_short' and 'ema_long' columns.
#
#     Returns:
#         str: 'BUY', 'SELL', or 'NONE'
#     """
#
#     required_columns = {"ema_short", "ema_long"}
#
#     if not required_columns.issubset(df.columns):
#         raise ValueError("DataFrame must contain 'ema_short' and 'ema_long' columns")
#
#     if len(df) < 2:
#         return "NONE"
#
#     # Compute difference between EMAs
#     diff = df["ema_short"] - df["ema_long"]
#
#     prev_diff = diff.shift(1)
#
#     # Detect crossover
#     buy_condition = (prev_diff < 0) & (diff > 0)
#     sell_condition = (prev_diff > 0) & (diff < 0)
#
#     if buy_condition.iloc[-1]:
#         return "BUY"
#     elif sell_condition.iloc[-1]:
#         return "SELL"
#     else:
#         return "NONE"
