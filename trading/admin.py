from django.contrib import admin
from .models import StockConfig, TradeState


@admin.register(StockConfig)
class StockConfigAdmin(admin.ModelAdmin):
    """
    Admin configuration for tradable instruments.
    """

    list_display = (
        "trading_symbol",
        "symbol_token",
        "exchange",
        "timeframe",
        "is_active",
    )

    list_filter = ("exchange", "timeframe", "is_active")

    search_fields = ("trading_symbol", "symbol_token")


@admin.register(TradeState)
class TradeStateAdmin(admin.ModelAdmin):
    """
    Admin configuration for trade state tracking.
    """

    list_display = ("symbol", "position", "last_signal", "updated_at")
    list_filter = ("position",)
