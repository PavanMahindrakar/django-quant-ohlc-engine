# config/trading/views.py
import json
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from trading.services.angelone_service import AngelOneService
from trading.engine.ema_pipeline import run_ema_pipeline
from trading.models import StockConfig, TradeState
from .forms import StockConfigForm
from trading.engine.trading_engine import TradingEngine
from django.conf import settings
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

# -------------------------------
# CRUD Views
# -------------------------------

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


# -------------------------------
# LIVE Signal Page (UI)
# -------------------------------

def generate_signals(request):
    """
    Reads active stocks from DB,
    runs EMA pipeline for each,
    and displays latest signal.
    """

    stocks = StockConfig.objects.filter(is_active=True)
    results = []

    print("Running LIVE EMA pipeline...")

    for stock in stocks:

        result = run_ema_pipeline(
            symbol_token=stock.symbol,
            interval=stock.timeframe,
            candle_count=100,
        )

        print(f"{stock.symbol} -> {result}")

        results.append({
            "symbol": stock.symbol,
            "exchange": stock.exchange,
            "timeframe": stock.timeframe,
            "signal": result.get("signal"),
            "last_close": result.get("last_close"),
            "error": result.get("error"),
        })

    return render(request, "trading/signals.html", {"results": results})


# -------------------------------
# DEBUG API (JSON View)
# -------------------------------

def api_signal_debug(request, symbol_token):
    """
    Debug Endpoint
    --------------

    Returns full EMA calculation details as JSON.

    Flow:
        1. Create SmartAPI service
        2. Login once
        3. Run EMA pipeline
        4. Return structured debug output
    """

    try:
        # ----------------------------------------
        # 1️⃣ Initialize SmartAPI service
        # ----------------------------------------
        service = AngelOneService()

        login_response = service.login()

        if not login_response.get("status"):
            return JsonResponse(
                {"error": "SmartAPI login failed"},
                status=500
            )

        # ----------------------------------------
        # 2️⃣ Run EMA pipeline
        # ----------------------------------------
        result = run_ema_pipeline(
            service=service,
            symbol_token=symbol_token,
            interval="ONE_MINUTE",
            candle_count=100,
        )

        # ----------------------------------------
        # 3️⃣ Return JSON response
        # ----------------------------------------
        return JsonResponse(result, safe=True)

    except Exception as e:
        return JsonResponse(
            {"error": str(e)},
            status=500
        )


def run_engine_demo(request):
    """
    Browser-based demo endpoint.

    Runs full TradingEngine for one stock
    and displays complete structured result.
    """

    stock = StockConfig.objects.filter(is_active=True).first()

    if not stock:
        return render(request, "trading/demo.html", {
            "error": "No active stock configured"
        })

    service = AngelOneService()
    login_resp = service.login()

    if not login_resp.get("status"):
        return render(request, "trading/demo.html", {
            "error": "Login failed"
        })

    engine = TradingEngine(
        service=service,
        dry_run=not settings.LIVE_TRADING_ENABLED
    )

    result = engine.run(
        symbol_token=stock.symbol_token,
        trading_symbol=stock.trading_symbol,
        exchange=stock.exchange,
        interval=stock.timeframe,
        candle_count=100,
        quantity=1,
    )

    # Fetch current DB state
    trade_state = TradeState.objects.filter(
        symbol=stock.trading_symbol
    ).first()

    return render(request, "trading/demo.html", {
        "stock": stock,
        "result": result,
        "trade_state": trade_state,
        "live_enabled": settings.LIVE_TRADING_ENABLED,
    })


@csrf_exempt
def engine_dashboard(request):
    """
    Interactive Trading Engine Dashboard.
    """

    stock = StockConfig.objects.filter(is_active=True).first()

    context = {
        "stock": stock,
        "mode": "dry",  # default
        "chart_data": "[]"
    }

    if not stock:
        context["error"] = "No active stock configured"
        return render(request, "trading/dashboard.html", context)

    if request.method == "POST":

        mode = request.POST.get("mode", "dry")
        # Live allowed only if BOTH selected AND globally enabled
        live_allowed = (
                mode == "live" and
                getattr(settings, "LIVE_TRADING_ENABLED", False)
        )
        dry_run = not live_allowed

        context["mode"] = mode

        service = AngelOneService()
        login_resp = service.login()

        if not login_resp.get("status"):
            context["error"] = "Login failed"
            return render(request, "trading/dashboard.html", context)

        engine = TradingEngine(service=service, dry_run=dry_run)

        result = engine.run(
            symbol_token=stock.symbol_token,
            trading_symbol=stock.trading_symbol,
            exchange=stock.exchange,
            interval=stock.timeframe,
            candle_count=50,
            quantity=getattr(settings, "DEFAULT_ORDER_QUANTITY", 1),
        )

        signal_data = result.get("signal_data", {})
        candles = signal_data.get("candles", [])

        context.update({
            "result": result,
            "trade_state": TradeState.objects.filter(
                symbol=stock.trading_symbol
            ).first(),
            "chart_data": json.dumps(candles),
        })

    return render(request, "trading/dashboard.html", context)
