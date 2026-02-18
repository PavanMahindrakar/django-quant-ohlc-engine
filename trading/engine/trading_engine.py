# config/trading/engine/trading_engine.py

from django.utils import timezone
from django.utils.dateparse import parse_datetime
from datetime import timedelta

from trading.engine.ema_pipeline import run_ema_pipeline
from trading.services.order_service import OrderService
from trading.models import SignalLog, StrategyConfig


class TradingEngine:

    def __init__(self, service, dry_run=True):
        self.service = service
        self.order_service = OrderService(service=service, dry_run=dry_run)

    def run(
        self,
        stock,
        quantity: int = 1,
    ) -> dict:

        # -------------------------------------------------
        # 1️⃣ Load Strategy Config
        # -------------------------------------------------
        try:
            strategy = stock.strategy
        except StrategyConfig.DoesNotExist:
            return {
                "status": "CONFIG_ERROR",
                "details": "StrategyConfig not defined for this stock"
            }

        # -------------------------------------------------
        # 2️⃣ Run EMA Pipeline (Dynamic Config)
        # -------------------------------------------------
        signal_data = run_ema_pipeline(
            service=self.service,
            symbol_token=stock.symbol_token,
            interval=stock.timeframe,
            candle_count=strategy.candle_count,
            short_span=strategy.short_span,
            long_span=strategy.long_span,
        )

        if "error" in signal_data:
            return {
                "status": "PIPELINE_ERROR",
                "details": signal_data,
            }

        signal = signal_data.get("signal")
        last_price = signal_data.get("last_close")

        # Use actual last crossover timestamp
        crossover_timestamp = signal_data.get("crossover_timestamp")

        candle_dt = parse_datetime(crossover_timestamp) if crossover_timestamp else None

        # signal = signal_data.get("signal")
        # last_price = signal_data.get("last_close")
        # candle_timestamp = signal_data.get("timestamp")
        #
        # candle_dt = parse_datetime(candle_timestamp)

        # -------------------------------------------------
        # 3️⃣ Log Signal
        # -------------------------------------------------
        signal_log = SignalLog.objects.create(
            stock=stock,
            signal=signal,
            price=last_price,
            ema_short=signal_data.get("ema_short"),
            ema_long=signal_data.get("ema_long"),
            diff=signal_data.get("diff"),
            crossover_timestamp=candle_dt,
            executed=False,
            generated_at=timezone.now()
        )

        print(f"\n📊 Signal Logged: {signal} @ {candle_dt}")

        # -------------------------------------------------
        # 4️⃣ Skip if No Signal
        # -------------------------------------------------
        if signal not in ["BUY", "SELL"]:
            return {
                "signal_data": signal_data,
                "order_result": {
                    "status": "SKIPPED",
                    "reason": "No fresh crossover"
                }
            }

        # -------------------------------------------------
        # 5️⃣ Freshness Check (Dynamic)
        # -------------------------------------------------
        now = timezone.now()
        freshness_limit = now - timedelta(
            minutes=strategy.signal_validity_minutes
        )

        if candle_dt < freshness_limit:
            return {
                "signal_data": signal_data,
                "order_result": {
                    "status": "STALE_SIGNAL",
                    "reason": "Signal older than validity window"
                }
            }

        # -------------------------------------------------
        # 6️⃣ Execute Order
        # -------------------------------------------------
        order_result = self.order_service.place_order(
            symbol_token=stock.symbol_token,
            trading_symbol=stock.trading_symbol,
            exchange=stock.exchange,
            signal=signal,
            quantity=quantity,
            last_price=last_price,
        )

        # -------------------------------------------------
        # 7️⃣ Mark Executed
        # -------------------------------------------------
        if order_result.get("status") in ["EXECUTED", "ORDER_SENT"]:
            signal_log.executed = True
            signal_log.save()
            print("✅ Signal marked as executed")

        return {
            "signal_data": signal_data,
            "order_result": order_result,
        }