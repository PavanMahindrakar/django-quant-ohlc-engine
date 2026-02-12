# trading/services/trading_engine.py

from trading.models import StockConfig
from trading.services.data_transformer import ohlc_to_dataframe
from trading.strategies.indicators import add_ema_columns
from trading.strategies.ema_crossover import ema_crossover_signal
from trading.services.order_service import OrderService


class TradingEngine:

    def __init__(self, dry_run=True):
        self.order_service = OrderService(dry_run=dry_run)

    def run(self):
        """
        Executes full trading pipeline.
        Returns structured results list.
        """

        active_stocks = StockConfig.objects.filter(is_active=True)

        results = []

        for stock in active_stocks:

            # Mock OHLC data (replace later with SmartAPI)
            mock_data = {
                "data": [
                    ["2026-02-12T09:15:00", 100, 100, 100, 100],
                    ["2026-02-12T09:16:00", 100, 100, 100, 101],
                    ["2026-02-12T09:17:00", 100, 100, 100, 102],
                    ["2026-02-12T09:18:00", 100, 100, 100, 103],
                    ["2026-02-12T09:19:00", 100, 100, 100, 104],
                    ["2026-02-12T09:20:00", 100, 100, 100, 105],
                    ["2026-02-12T09:21:00", 100, 100, 100, 104],
                    ["2026-02-12T09:22:00", 100, 100, 100, 90],
                ]
            }

            df = ohlc_to_dataframe(mock_data)
            df = add_ema_columns(df)
            signal = ema_crossover_signal(df)

            order_result = None

            if signal in ["BUY", "SELL"]:
                order_result = self.order_service.place_order(
                    symbol=stock.symbol,
                    exchange=stock.exchange,
                    signal=signal
                )

            results.append({
                "symbol": stock.symbol,
                "exchange": stock.exchange,
                "timeframe": stock.timeframe,
                "signal": signal,
                "order_status": order_result
            })

        return results
