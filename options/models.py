from django.db import models

class OptionChainSnapshot(models.Model):
    symbol = models.CharField(max_length=20)
    expiry = models.CharField(max_length=20)
    spot = models.FloatField()

    raw_data = models.JSONField()

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.symbol} - {self.expiry} - {self.created_at}"