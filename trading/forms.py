# config/trading/forms.py

from django import forms
from django.core.exceptions import ValidationError
from .models import StockConfig, StrategyConfig


class CombinedConfigForm(forms.ModelForm):
    """
    Institutional Combined Configuration Form.

    Handles:
    - Instrument configuration (StockConfig)
    - EMA strategy parameters (StrategyConfig)
    - Business validation
    """

    # --- Strategy Fields ---
    short_span = forms.IntegerField(min_value=1, label="Short EMA Span")
    long_span = forms.IntegerField(min_value=1, label="Long EMA Span")
    candle_count = forms.IntegerField(min_value=20, label="Candle Count")
    signal_validity_minutes = forms.IntegerField(
        min_value=1,
        label="Signal Validity (minutes)"
    )

    class Meta:
        model = StockConfig
        fields = [
            "symbol_token",
            "trading_symbol",
            "exchange",
            "timeframe",
            "is_active",
        ]

    # -------------------------------------------------
    # Validation Layer
    # -------------------------------------------------

    def clean(self):
        cleaned_data = super().clean()

        short_span = cleaned_data.get("short_span")
        long_span = cleaned_data.get("long_span")

        if short_span and long_span:
            if short_span >= long_span:
                raise ValidationError(
                    "Short EMA span must be smaller than Long EMA span."
                )

        return cleaned_data

    # -------------------------------------------------
    # Save Logic (Handles StrategyConfig too)
    # -------------------------------------------------

    def save(self, commit=True):
        stock = super().save(commit)

        strategy, _ = StrategyConfig.objects.get_or_create(stock=stock)

        strategy.short_span = self.cleaned_data["short_span"]
        strategy.long_span = self.cleaned_data["long_span"]
        strategy.candle_count = self.cleaned_data["candle_count"]
        strategy.signal_validity_minutes = self.cleaned_data["signal_validity_minutes"]
        strategy.save()

        return stock