import pandas as pd


def ohlc_to_dataframe(ohlc_list) -> pd.DataFrame:
    """
    Convert SmartAPI OHLC list into clean pandas DataFrame.

    Expected Input:
        [
            [timestamp, open, high, low, close, volume],
            ...
        ]

    Output:
        DataFrame with:
            - timezone-aware datetime index
            - float OHLC columns
            - sorted in ascending order
    """

    if not ohlc_list:
        raise ValueError("Empty OHLC data received")

    # Create DataFrame
    df = pd.DataFrame(
        ohlc_list,
        columns=["timestamp", "open", "high", "low", "close", "volume"]
    )

    # Convert timestamp → datetime (keeps timezone)
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    # Set as index
    df.set_index("timestamp", inplace=True)

    # Convert numeric columns
    df[["open", "high", "low", "close", "volume"]] = df[
        ["open", "high", "low", "close", "volume"]
    ].astype(float)

    # Ensure sorted order (critical for EMA correctness)
    df.sort_index(inplace=True)

    return df


#  dummy data function
# def ohlc_to_dataframe(raw_response: dict) -> pd.DataFrame:
#     """
#     Convert raw OHLC API response into clean pandas DataFrame.
#
#     :param raw_response: Raw JSON response from broker
#     :return: Clean OHLC DataFrame
#     """
#
#     if "data" not in raw_response:
#         raise ValueError("Invalid OHLC response format")
#
#     # Extract candle data list
#     candles = raw_response["data"]
#
#     # Create DataFrame with proper column names
#     df = pd.DataFrame(
#         candles,
#         columns=["timestamp", "open", "high", "low", "close"]
#     )
#
#     # Convert timestamp column to datetime
#     df["timestamp"] = pd.to_datetime(df["timestamp"])
#
#     # Set timestamp as index
#     df.set_index("timestamp", inplace=True)
#
#     # Ensure numeric columns are floats
#     df[["open", "high", "low", "close"]] = df[
#         ["open", "high", "low", "close"]
#     ].astype(float)
#
#     # Sort by time (important for strategies)
#     df.sort_index(inplace=True)
#
#     return df
