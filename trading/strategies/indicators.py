import pandas as pd
import numpy as np


def add_ema_columns(df: pd.DataFrame, short_span: int = 9, long_span: int = 21) -> pd.DataFrame:
    """
    Add short and long EMA columns to OHLC DataFrame.

    :param df: DataFrame with 'close' column
    :param short_span: Period for short EMA
    :param long_span: Period for long EMA
    :return: DataFrame with EMA columns added
    """

    if "close" not in df.columns:
        raise ValueError("DataFrame must contain 'close' column")

    # Calculate short EMA
    df["ema_short"] = df["close"].ewm(
        span=short_span,
        adjust=False
    ).mean()

    # Calculate long EMA
    df["ema_long"] = df["close"].ewm(
        span=long_span,
        adjust=False
    ).mean()

    return df
