"""
BatchTradingEngine

Responsible for:
1. Logging into SmartAPI once
2. Looping through active stocks in DB
3. Running TradingEngine per stock
"""

from trading.models import StockConfig
from trading.engine.trading_engine import TradingEngine
from trading.services.angelone_service import AngelOneService


class BatchTradingEngine:
    """
    Batch-level trading executor.
    """

    def __init__(self, dry_run=True):
        self.dry_run = dry_run
        self.trading_engine = TradingEngine(dry_run=dry_run)
        self.service = AngelOneService()

    def run(self):
        """
        Executes trading cycle for all active DB stocks.
        """

        results = []

        # 🔐 Login once (important to avoid rate limit issues)
        login_response = self.service.login()

        if not login_response.get("status"):
            return [{"error": "SmartAPI login failed"}]

        active_stocks = StockConfig.objects.filter(is_active=True)

        for stock in active_stocks:

            result = self.trading_engine.run(
                service=self.service,
                symbol_token=stock.symbol,
                exchange=stock.exchange,
                interval=stock.timeframe,
                candle_count=100,
            )

            results.append({
                "symbol": stock.symbol,
                "result": result,
            })

        return results
