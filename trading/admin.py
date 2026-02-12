from django.contrib import admin
from .models import StockConfig


@admin.register(StockConfig)
class StockConfigAdmin(admin.ModelAdmin):
    list_display = ("symbol", "exchange", "timeframe", "is_active")
    list_filter = ("exchange", "timeframe", "is_active")
    search_fields = ("symbol",)
