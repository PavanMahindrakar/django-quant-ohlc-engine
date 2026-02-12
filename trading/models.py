from django.db import models
from django.utils import timezone


class StockConfig(models.Model):
    symbol = models.CharField(
        max_length=20,
        help_text="SmartAPI symbol token (e.g. 3045 for RELIANCE)"
    )

    exchange = models.CharField(
        max_length=20,
        help_text="Exchange name (e.g. NSE)"
    )

    timeframe = models.CharField(
        max_length=20,
        help_text="SmartAPI interval (e.g. ONE_MINUTE, FIVE_MINUTE)"
    )

    is_active = models.BooleanField(
        default=True,
        help_text="Enable/Disable this stock for live signal generation"
    )

    class Meta:
        unique_together = ("symbol", "exchange", "timeframe")

    def __str__(self):
        return f"{self.symbol} | {self.exchange} | {self.timeframe}"
