# config/trading/models.py
from django.db import models
from django.utils import timezone

class StockConfig(models.Model):
    """
    Stores tradable instrument configuration.

    Important:
    - symbol_token → used for fetching OHLC from SmartAPI
    - trading_symbol → used for placing orders
    - exchange → NSE / BSE etc.
    - timeframe → Candle interval
    """

    symbol_token = models.CharField(
        max_length=20,
        help_text="SmartAPI symbol token (e.g. 3045 for RELIANCE)"
    )

    trading_symbol = models.CharField(
        max_length=50,
        help_text="SmartAPI trading symbol (e.g. RELIANCE-EQ)"
    )

    exchange = models.CharField(
        max_length=20,
        help_text="Exchange name (e.g. NSE)"
    )

    timeframe = models.CharField(
        max_length=20,
        help_text="SmartAPI interval (e.g. ONE_MINUTE)"
    )

    is_active = models.BooleanField(
        default=True,
        help_text="Enable/Disable this stock for trading"
    )

    class Meta:
        unique_together = ("symbol_token", "exchange", "timeframe")

    def __str__(self):
        return f"{self.trading_symbol} ({self.symbol_token}) | {self.exchange}"


class TradeState(models.Model):
    """
    Tracks current trading position per symbol.

    Used for:
    - Preventing duplicate orders
    - Tracking open positions
    - Safe execution control
    """

    POSITION_CHOICES = [
        ("NONE", "None"),
        ("LONG", "Long"),
    ]

    symbol = models.CharField(max_length=20, unique=True)

    position = models.CharField(
        max_length=10,
        choices=POSITION_CHOICES,
        default="NONE",
    )

    last_signal = models.CharField(max_length=10, default="NONE")

    updated_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.symbol} - {self.position}"
