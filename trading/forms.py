from django import forms
from .models import StockConfig


class StockConfigForm(forms.ModelForm):
    class Meta:
        model = StockConfig
        fields = ["symbol", "exchange", "timeframe", "is_active"]
