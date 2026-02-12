# trading/services/order_service.py

import logging
from django.conf import settings
from trading.models import TradeState
from django.utils import timezone

logger = logging.getLogger(__name__)


class OrderService:

    def __init__(self, dry_run=True):
        """
        dry_run=True → No real order placed.
        dry_run=False → Real API call.
        """
        self.dry_run = dry_run


    def place_order(self, symbol, exchange, signal):

        if signal not in ["BUY", "SELL"]:
            logger.info(f"No valid signal for {symbol}. Skipping order.")
            return {"status": "SKIPPED", "reason": "No valid signal"}

        # Get or create state record
        trade_state, created = TradeState.objects.get_or_create(
            symbol=symbol
        )

        current_position = trade_state.position

        logger.info(f"Current position for {symbol}: {current_position}")

        # Prevent duplicate BUY
        if signal == "BUY" and current_position == "LONG":
            logger.info(f"Duplicate BUY prevented for {symbol}")
            return {"status": "BLOCKED", "reason": "Already LONG"}

        # Prevent duplicate SELL
        if signal == "SELL" and current_position == "SHORT":
            logger.info(f"Duplicate SELL prevented for {symbol}")
            return {"status": "BLOCKED", "reason": "Already SHORT"}

        # Determine new position
        new_position = "LONG" if signal == "BUY" else "SHORT"

        if self.dry_run:
            logger.info(f"[DRY RUN] {signal} order for {symbol}")
        else:
            logger.info(f"[LIVE] Executing {signal} for {symbol}")
            # Real API call would go here

        # Update DB state
        trade_state.position = new_position
        trade_state.last_signal = signal
        trade_state.updated_at = timezone.now()
        trade_state.save()

        return {
            "status": "EXECUTED" if not self.dry_run else "DRY_RUN",
            "symbol": symbol,
            "new_position": new_position
        }


    # def place_order(self, symbol, exchange, signal):
    #     """
    #     Places order based on signal.
    #     """

    #     if signal not in ["BUY", "SELL"]:
    #         logger.info(f"No valid signal for {symbol}. Skipping order.")
    #         return {"status": "SKIPPED", "reason": "No valid signal"}

    #     # 🚨 Safety Check 1: Prevent duplicate execution
    #     # In real production, this should check DB or position state.
    #     logger.info(f"Preparing order: {symbol} | {signal}")

    #     if self.dry_run:
    #         logger.info(f"[DRY RUN] Order not executed for {symbol}")
    #         return {
    #             "status": "DRY_RUN",
    #             "symbol": symbol,
    #             "signal": signal
    #         }

    #     # 🚀 Real API execution would go here
    #     try:
    #         # placeholder for real SmartAPI call
    #         logger.info(f"Executing LIVE order for {symbol}")

    #         # response = smart_api.place_order(...)
    #         # return response

    #         return {"status": "LIVE_EXECUTED"}

    #     except Exception as e:
    #         logger.error(f"Order execution failed: {str(e)}")
    #         return {"status": "FAILED", "error": str(e)}
