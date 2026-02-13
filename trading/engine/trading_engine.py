"""
TradingEngine (Single-Symbol Orchestrator)

High-level orchestration layer responsible for:

1. Calling EMA strategy pipeline
2. Passing generated signal to OrderService
3. Returning structured execution result

This layer:
- Does NOT handle login
- Expects a logged-in AngelOneService instance
- Supports both dry-run and real trading modes
"""

from trading.engine.ema_pipeline import run_ema_pipeline
from trading.services.order_service import OrderService


class TradingEngine:
    """
    Symbol-level trading orchestrator.

    This class coordinates:
    - Strategy signal generation
    - Order execution
    - Risk control via OrderService

    It does NOT:
    - Manage DB stock configs
    - Handle broker authentication
    - Loop multiple symbols

    It operates on a single symbol per execution.
    """

    def __init__(self, service, dry_run=True):
        """
        Initialize trading engine.

        Parameters
        ----------
        service : AngelOneService
            Logged-in SmartAPI wrapper instance.

        dry_run : bool
            If True → no real broker orders are placed.
            If False → real execution allowed (subject to kill switch).
        """
        self.service = service
        self.order_service = OrderService(
            service=service,
            dry_run=dry_run
        )

    def run(
        self,
        symbol_token: str,
        trading_symbol: str,
        exchange: str,
        interval: str = "ONE_MINUTE",
        candle_count: int = 100,
        quantity: int = 1,
    ) -> dict:
        """
        Execute full lifecycle for a single symbol.

        Flow
        ----
        1. Fetch market data and compute EMA crossover
        2. Extract trading signal
        3. Pass signal to OrderService
        4. Return combined structured response

        Parameters
        ----------
        symbol_token : str
            SmartAPI token used for fetching OHLC data.

        trading_symbol : str
            SmartAPI trading symbol used for order placement.

        exchange : str
            Exchange name (e.g., NSE).

        interval : str
            Candle timeframe (default: ONE_MINUTE).

        candle_count : int
            Number of candles to fetch.

        quantity : int
            Order quantity.

        Returns
        -------
        dict
            Structured response containing:
            - signal_data
            - order_result
        """

        # 1️⃣ Generate EMA strategy signal
        signal_data = run_ema_pipeline(
            service=self.service,
            symbol_token=symbol_token,
            interval=interval,
            candle_count=candle_count,
        )

        # Stop execution if strategy pipeline failed
        if "error" in signal_data:
            return {
                "status": "PIPELINE_ERROR",
                "details": signal_data,
            }

        signal = signal_data.get("signal")
        last_price = signal_data.get("last_close")

        # 2️⃣ Execute order safely
        order_result = self.order_service.place_order(
            symbol_token=symbol_token,
            trading_symbol=trading_symbol,
            exchange=exchange,
            signal=signal,
            quantity=quantity,
            last_price=last_price,
        )

        return {
            "signal_data": signal_data,
            "order_result": order_result,
        }
