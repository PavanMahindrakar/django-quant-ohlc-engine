# config/trading/models.py

from django.db import models
from django.utils import timezone


class StockConfig(models.Model):
    """
    Stores tradable instrument configuration.
    """

    symbol_token = models.CharField(
        max_length=20,
        help_text="SmartAPI symbol token (e.g. 2885 for RELIANCE)"
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

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ("symbol_token", "exchange", "timeframe")

    def __str__(self):
        return f"{self.trading_symbol} ({self.exchange})"


# ==========================================================
# STRATEGY CONFIG (Separated Layer)
# ==========================================================

class StrategyConfig(models.Model):
    """
    EMA Strategy parameters per stock.
    """

    stock = models.OneToOneField(
        StockConfig,
        on_delete=models.CASCADE,
        related_name="strategy"
    )

    short_span = models.IntegerField(default=9)
    long_span = models.IntegerField(default=21)
    candle_count = models.IntegerField(default=100)

    signal_validity_minutes = models.IntegerField(
        default=5,
        help_text="Signal must be executed within this many minutes"
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"EMA Strategy → {self.stock.trading_symbol}"


# ==========================================================
# SIGNAL LOG (Institutional Logging)
# ==========================================================

class SignalLog(models.Model):

    SIGNAL_CHOICES = [
        ("BUY", "BUY"),
        ("SELL", "SELL"),
        ("NO SIGNAL", "NO SIGNAL"),
    ]

    stock = models.ForeignKey(
        StockConfig,
        on_delete=models.CASCADE
    )

    signal = models.CharField(max_length=15, choices=SIGNAL_CHOICES)

    crossover_timestamp = models.DateTimeField()
    generated_at = models.DateTimeField(default=timezone.now)

    price = models.FloatField()

    ema_short = models.FloatField()
    ema_long = models.FloatField()
    diff = models.FloatField()

    executed = models.BooleanField(default=False)

    class Meta:
        ordering = ["-generated_at"]

    def __str__(self):
        return f"{self.stock.trading_symbol} | {self.signal} | {self.generated_at}"

# ==========================================================
# ORDER LOG (Execution Layer)
# ==========================================================

class OrderLog(models.Model):
    """
    Stores broker execution details.
    Linked to SignalLog.
    """

    signal = models.ForeignKey(
        SignalLog,
        on_delete=models.CASCADE,
        related_name="orders"
    )

    order_id = models.CharField(max_length=100, null=True, blank=True)
    broker_status = models.CharField(max_length=50, null=True, blank=True)

    quantity = models.IntegerField()
    order_type = models.CharField(max_length=20, default="MARKET")

    broker_response = models.JSONField(null=True, blank=True)

    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.signal.stock.trading_symbol} | {self.order_id}"

# ==========================================================
# TRADE STATE
# ==========================================================

class TradeState(models.Model):

    POSITION_CHOICES = [
        ("NONE", "None"),
        ("LONG", "Long"),
    ]

    symbol = models.CharField(max_length=50, unique=True)

    position = models.CharField(
        max_length=10,
        choices=POSITION_CHOICES,
        default="NONE",
    )

    last_signal = models.CharField(max_length=10, default="NONE")

    updated_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.symbol} - {self.position}"