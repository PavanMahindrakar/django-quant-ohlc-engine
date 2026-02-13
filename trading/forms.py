from django import forms
from .models import StockConfig


class StockConfigForm(forms.ModelForm):
    """
    Form for creating/updating tradable instruments.
    """

    class Meta:
        model = StockConfig
        fields = [
            "symbol_token",
            "trading_symbol",
            "exchange",
            "timeframe",
            "is_active",
        ]
