# config/trading/views.py

import json
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.utils import timezone

from trading.models import StockConfig, TradeState
from trading.services.angelone_service import AngelOneService
from trading.engine.trading_engine import TradingEngine
from .forms import StockConfigForm


# ==========================================================
# CRUD VIEWS
# ==========================================================

def stock_list(request):
    stocks = StockConfig.objects.all()
    return render(request, "trading/stock_list.html", {"stocks": stocks})


def stock_create(request):
    if request.method == "POST":
        form = StockConfigForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("stock_list")
    else:
        form = StockConfigForm()

    return render(request, "trading/stock_form.html", {"form": form})


def stock_update(request, pk):
    stock = get_object_or_404(StockConfig, pk=pk)

    if request.method == "POST":
        form = StockConfigForm(request.POST, instance=stock)
        if form.is_valid():
            form.save()
            return redirect("stock_list")
    else:
        form = StockConfigForm(instance=stock)

    return render(request, "trading/stock_form.html", {"form": form})


def stock_delete(request, pk):
    stock = get_object_or_404(StockConfig, pk=pk)

    if request.method == "POST":
        stock.delete()
        return redirect("stock_list")

    return render(request, "trading/stock_confirm_delete.html", {"stock": stock})


# ==========================================================
# DASHBOARD PAGE (UI ONLY)
# ==========================================================

def dashboard_page(request):
    """
    Renders trading terminal UI only.
    No execution logic here.
    """

    stock = StockConfig.objects.filter(is_active=True).first()

    return render(request, "trading/dashboard.html", {
        "stock": stock,
        "live_enabled": getattr(settings, "LIVE_TRADING_ENABLED", False)
    })


# ==========================================================
# ENGINE EXECUTION API (AJAX POST)
# ==========================================================

@csrf_exempt
def engine_run_api(request):
    """
    AJAX endpoint for running trading engine.

    Flow:
    - Login
    - Run strategy
    - Risk management
    - Place order (if allowed)
    - Return structured JSON response
    """

    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    stock = StockConfig.objects.filter(is_active=True).first()

    if not stock:
        return JsonResponse({"error": "No active stock configured"}, status=400)

    mode = request.POST.get("mode", "dry")

    live_allowed = (
        mode == "live" and
        getattr(settings, "LIVE_TRADING_ENABLED", False)
    )

    dry_run = not live_allowed

    # ---------------- LOGIN ----------------
    service = AngelOneService()
    login_resp = service.login()

    login_time = timezone.now().strftime("%Y-%m-%d %H:%M:%S")

    if not login_resp.get("status"):
        return JsonResponse({"error": "Login failed"}, status=500)

    # ---------------- ENGINE ----------------
    engine = TradingEngine(service=service, dry_run=dry_run)

    result = engine.run(
        symbol_token=stock.symbol_token,
        trading_symbol=stock.trading_symbol,
        exchange=stock.exchange,
        interval=stock.timeframe,
        candle_count=50,
        quantity=getattr(settings, "DEFAULT_ORDER_QUANTITY", 1),
    )

    # ---------------- BROKER SNAPSHOT ----------------
    # -------- Safe Broker Calls --------
    try:
        margin = service.smart.rmsLimit()
    except Exception as e:
        margin = {"status": False, "error": str(e)}

    try:
        orderbook_resp = service.smart.orderBook()
        orderbook = orderbook_resp.get("data", []) if orderbook_resp else []
    except Exception as e:
        orderbook = []

    filtered_orders = [
        o for o in orderbook
        if o.get("tradingsymbol") == stock.trading_symbol
    ]

    trade_state = TradeState.objects.filter(
        symbol=stock.trading_symbol
    ).first()

    # After login
    login_data = {
        "status": login_resp.get("status"),
        "clientcode": login_resp.get("data", {}).get("clientcode"),
        "message": login_resp.get("message"),
        "login_time": timezone.now().isoformat()
    }

    signal_data = result.get("signal_data", {})
    candles = signal_data.get("candles", [])

    # Remove candles from signal panel
    clean_signal = {
        "signal": signal_data.get("signal"),
        "timestamp": signal_data.get("timestamp"),
        "last_close": signal_data.get("last_close"),
        "ema_short": signal_data.get("ema_short"),
        "ema_long": signal_data.get("ema_long"),
        "diff": signal_data.get("diff"),
    }

    # DataFrame debug info
    df_debug = {
        "rows": len(candles),
        "columns": list(candles[0].keys()) if candles else []
    }

    preview_count = 5  # change to 2 if you want

    return JsonResponse({
        "login": login_data,
        "signal": clean_signal,

        # 🔹 Only preview subset
        "ohlc_preview": candles[-preview_count:],

        # 🔹 Metadata
        "ohlc_meta": {
            "total_candles": len(candles),
            "first_timestamp": candles[0]["timestamp"] if candles else None,
            "last_timestamp": candles[-1]["timestamp"] if candles else None,
        },

        "df_debug": df_debug,
        "order_result": result.get("order_result"),
        "margin": margin,
        "trade_state": {
            "position": trade_state.position if trade_state else "NONE",
            "last_signal": trade_state.last_signal if trade_state else "NONE",
        },
        "orders": filtered_orders,
        "server_time": timezone.now().isoformat()
    })