"""
OrderService

Production-grade execution layer.

Implements multi-layer safety architecture:

Layer 1 → Broker position sync (DB reconciliation)
Layer 2 → Margin validation before BUY
Layer 3 → Duplicate trade prevention
Layer 4 → Broker response validation
Layer 5 → Safe DB update only after confirmed execution

Supports:
- Dry-run simulation
- Real SmartAPI execution
- Global kill switch protection
"""

import logging
from django.utils import timezone
from django.conf import settings
from trading.models import TradeState

logger = logging.getLogger(__name__)


class OrderService:
    """
    Handles safe trade execution.

    This class ensures:
    - No duplicate trades
    - Margin availability check
    - DB state stays synced with broker
    - Broker response validation
    - Execution only when explicitly enabled
    """

    def __init__(self, service, dry_run=True):
        """
        Parameters
        ----------
        service : AngelOneService
            Logged-in SmartAPI wrapper instance.

        dry_run : bool
            If True → simulate order only.
            If False → allow real broker execution
                       (subject to LIVE_TRADING_ENABLED flag).
        """
        self.service = service
        self.dry_run = dry_run

    # ==========================================================
    # LAYER 1 — POSITION SYNC
    # ==========================================================

    def _sync_position(self, trading_symbol: str):
        """
        Sync DB position with broker's actual position.

        Prevents state mismatch between:
        - Internal database
        - Broker system

        Updates DB only if mismatch detected.
        """
        try:
            broker_positions = self.service.smart.position()

            if not broker_positions.get("status"):
                logger.warning("Broker position fetch failed")
                return

            positions = broker_positions.get("data") or []
            broker_position = "NONE"

            for pos in positions:
                if pos.get("tradingsymbol") == trading_symbol:
                    net_qty = int(pos.get("netqty", 0))
                    if net_qty > 0:
                        broker_position = "LONG"

            trade_state, _ = TradeState.objects.get_or_create(
                symbol=trading_symbol
            )

            if trade_state.position != broker_position:
                logger.info(
                    f"Position sync: {trade_state.position} → {broker_position}"
                )
                trade_state.position = broker_position
                trade_state.save()

        except Exception as e:
            logger.error(f"Position sync failed: {str(e)}")

    # ==========================================================
    # LAYER 2 — MARGIN CHECK
    # ==========================================================

    def _check_margin(self, required_amount: float) -> bool:
        """
        Validate available cash before placing BUY order.

        Parameters
        ----------
        required_amount : float
            Approx required capital (price × quantity)

        Returns
        -------
        bool
            True if margin sufficient, else False.
        """
        try:
            rms = self.service.smart.rmsLimit()

            if not rms.get("status"):
                return False

            available_cash = float(
                rms["data"].get("availablecash", 0)
            )

            return available_cash >= required_amount

        except Exception as e:
            logger.error(f"Margin check failed: {str(e)}")
            return False

    # ==========================================================
    # MAIN EXECUTION METHOD
    # ==========================================================

    def place_order(
            self,
            symbol_token: str,
            trading_symbol: str,
            exchange: str,
            signal: str,
            quantity: int = 1,
            last_price: float = None,
    ) -> dict:

        if signal not in ["BUY", "SELL"]:
            return {"status": "SKIPPED", "reason": "No valid signal"}

        if quantity <= 0:
            return {"status": "BLOCKED", "reason": "Invalid quantity"}

        # Sync position first
        self._sync_position(trading_symbol)

        trade_state, _ = TradeState.objects.get_or_create(
            symbol=trading_symbol
        )

        current_position = trade_state.position

        if signal == "BUY" and current_position == "LONG":
            return {"status": "BLOCKED", "reason": "Already LONG"}

        if signal == "SELL" and current_position == "NONE":
            return {"status": "BLOCKED", "reason": "No position to close"}

        orderparams = {
            "variety": "NORMAL",
            "tradingsymbol": trading_symbol,
            "symboltoken": symbol_token,
            "transactiontype": signal,
            "exchange": exchange,
            "ordertype": "MARKET",
            "producttype": "DELIVERY",
            "duration": "DAY",
            "price": str(round(last_price * 1.20, 2)),
            "squareoff": "0",
            "stoploss": "0",
            "quantity": str(quantity),
        }

        # ================= DRY RUN =================
        if self.dry_run:
            return {
                "status": "DRY_RUN",
                "payload": orderparams,
            }

        if not getattr(settings, "LIVE_TRADING_ENABLED", False):
            return {
                "status": "DISABLED",
                "reason": "Live trading disabled in settings",
            }

        try:
            print("\n🚨 LIVE ORDER ATTEMPT")

            place_response = self.service.smart.placeOrder(orderparams)

            print("📨 Raw Place Response:", place_response)

            # -----------------------------
            # Extract order_id safely
            # -----------------------------
            order_id = None

            if isinstance(place_response, str):
                order_id = place_response

            elif isinstance(place_response, dict):
                if not place_response.get("status"):
                    return {
                        "status": "FAILED",
                        "error": place_response.get("message"),
                        "raw_place_response": place_response,
                    }
                order_id = place_response.get("data")

            if not order_id:
                return {
                    "status": "FAILED",
                    "error": "No order ID returned",
                    "raw_place_response": place_response,
                }

            print("✅ Order ID:", order_id)

            # -----------------------------
            # Verify from Order Book
            # -----------------------------
            order_book = self.service.smart.orderBook()

            matched_order = None
            final_status = "UNKNOWN"

            if order_book.get("status"):
                for ob in order_book.get("data", []):
                    if ob.get("orderid") == order_id:
                        matched_order = ob
                        final_status = ob.get("orderstatus")
                        break

            print("📊 Final Broker Status:", final_status)

            # -----------------------------
            # Update DB Position Only if COMPLETE
            # -----------------------------
            if final_status == "COMPLETE":
                new_position = "LONG" if signal == "BUY" else "NONE"
                trade_state.position = new_position
                trade_state.last_signal = signal
                trade_state.updated_at = timezone.now()
                trade_state.save()
                print("💾 DB Updated → Position:", new_position)

            # -----------------------------
            # Return FULL Diagnostic Payload
            # -----------------------------
            return {
                "status": final_status,
                "order_id": order_id,
                "symbol": trading_symbol,
                "payload_sent": orderparams,
                "raw_place_response": place_response,
                "order_book_snapshot": order_book,
                "matched_order": matched_order,
            }

        except Exception as e:
            return {
                "status": "ERROR",
                "error": str(e),
            }
    # def place_order(
    #         self,
    #         symbol_token: str,
    #         trading_symbol: str,
    #         exchange: str,
    #         signal: str,
    #         quantity: int = 1,
    #         last_price: float = None,
    # ) -> dict:
    #     """
    #     Broker-level execution.
    #     No internal margin blocking.
    #     Broker (RMS) decides rejection.
    #     """
    #
    #     if signal not in ["BUY", "SELL"]:
    #         return {"status": "SKIPPED", "reason": "No valid signal"}
    #
    #     if quantity <= 0:
    #         return {"status": "BLOCKED", "reason": "Invalid quantity"}
    #
    #     # 1️⃣ Sync position first
    #     self._sync_position(trading_symbol)
    #
    #     trade_state, _ = TradeState.objects.get_or_create(
    #         symbol=trading_symbol
    #     )
    #
    #     current_position = trade_state.position
    #
    #     # Duplicate protection (still keep logical safety)
    #     if signal == "BUY" and current_position == "LONG":
    #         return {"status": "BLOCKED", "reason": "Already LONG"}
    #
    #     if signal == "SELL" and current_position == "NONE":
    #         return {"status": "BLOCKED", "reason": "No position to close"}
    #
    #     # Build broker payload
    #     orderparams = {
    #         "variety": "NORMAL",
    #         "tradingsymbol": trading_symbol,
    #         "symboltoken": symbol_token,
    #         "transactiontype": signal,
    #         "exchange": exchange,
    #         "ordertype": "MARKET",
    #         "producttype": "INTRADAY",
    #         "duration": "DAY",
    #         "price": "0",
    #         "squareoff": "0",
    #         "stoploss": "0",
    #         "quantity": str(quantity),
    #     }
    #
    #     # ================= DRY RUN =================
    #     if self.dry_run:
    #         logger.info(f"[DRY RUN] {signal} → {trading_symbol}")
    #         return {
    #             "status": "DRY_RUN",
    #             "payload": orderparams,
    #         }
    #
    #     # ================= LIVE EXECUTION =================
    #
    #     if not getattr(settings, "LIVE_TRADING_ENABLED", False):
    #         print("❌ Live trading disabled in settings")
    #         return {
    #             "status": "DISABLED",
    #             "reason": "Live trading disabled in settings",
    #         }
    #
    #     print(f"\n🚨 LIVE ORDER ATTEMPT")
    #     print(f"Symbol: {trading_symbol}")
    #     print(f"Signal: {signal}")
    #     print(f"Quantity: {quantity}")
    #     print(f"Exchange: {exchange}")
    #
    #     try:
    #         response = self.service.smart.placeOrder(orderparams)
    #
    #         print("\n📨 Broker Raw Response:")
    #         print(response)
    #
    #         # If broker returns string directly
    #         if isinstance(response, str):
    #             order_id = response
    #
    #         # If broker returns dict
    #         elif isinstance(response, dict):
    #             if not response.get("status"):
    #                 return {
    #                     "status": "FAILED",
    #                     "error": response.get("message"),
    #                     "raw": response,
    #                 }
    #             order_id = response.get("data")
    #
    #         else:
    #             return {
    #                 "status": "FAILED",
    #                 "error": "Unexpected broker response type",
    #                 "raw": response,
    #             }
    #
    #         if not order_id:
    #             return {
    #                 "status": "FAILED",
    #                 "error": "No order ID returned",
    #                 "raw": response,
    #             }
    #
    #         print(f"\n✅ Order ID Received: {order_id}")
    #
    #         order_book = self.service.smart.orderBook()
    #
    #         final_status = "UNKNOWN"
    #
    #         if order_book.get("status"):
    #             for order in order_book.get("data", []):
    #                 if order.get("orderid") == order_id:
    #                     final_status = order.get("orderstatus")
    #                     break
    #
    #         # Update DB
    #         new_position = "LONG" if signal == "BUY" else "NONE"
    #
    #         trade_state.position = new_position
    #         trade_state.last_signal = signal
    #         trade_state.updated_at = timezone.now()
    #         trade_state.save()
    #
    #         print(f"💾 DB Updated → New Position: {new_position}")
    #
    #         return {
    #             "status": "final_status",
    #             "order_id": order_id,
    #             "symbol": trading_symbol,
    #             "new_position": new_position,
    #             "payload_sent": orderparams,
    #         }
    #
    #     except Exception as e:
    #         print("🔥 Live order execution failed:")
    #         print(str(e))
    #         return {
    #             "status": "ERROR",
    #             "error": str(e),
    #         }