# config/trading/views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.utils import timezone

from trading.models import (
    StockConfig,
    TradeState,
    SignalLog,
    StrategyConfig,
)
from trading.services.angelone_service import AngelOneService
from trading.engine.trading_engine import TradingEngine
from trading.forms import CombinedConfigForm


# ==========================================================
# INSTITUTIONAL CONFIG PANEL (Replaces Admin)
# ==========================================================

def config_panel(request, pk=None):
    """
    Institutional Stock + Strategy Configuration Panel.
    Handles:
    - Create new instrument
    - Edit existing instrument
    - Strategy configuration
    """

    instance = None

    if pk:
        instance = get_object_or_404(StockConfig, pk=pk)

    if request.method == "POST":
        form = CombinedConfigForm(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            return redirect("config_panel")
    else:
        initial_data = {}

        if instance and hasattr(instance, "strategy"):
            strategy = instance.strategy
            initial_data = {
                "short_span": strategy.short_span,
                "long_span": strategy.long_span,
                "candle_count": strategy.candle_count,
                "signal_validity_minutes": strategy.signal_validity_minutes,
            }

        form = CombinedConfigForm(instance=instance, initial=initial_data)

    stocks = StockConfig.objects.all().select_related("strategy")

    return render(request, "trading/config_panel.html", {
        "form": form,
        "stocks": stocks
    })


# ==========================================================
# DASHBOARD
# ==========================================================

def dashboard_page(request):
    stock = StockConfig.objects.filter(is_active=True).first()

    return render(request, "trading/dashboard.html", {
        "stock": stock,
        "live_enabled": getattr(settings, "LIVE_TRADING_ENABLED", False)
    })


# ==========================================================
# ENGINE API
# ==========================================================
@csrf_exempt
def engine_run_api(request):

    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    stock = StockConfig.objects.filter(is_active=True).select_related("strategy").first()

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

    if not login_resp.get("status"):
        return JsonResponse({"error": "Login failed"}, status=500)

    # ---------------- ENGINE ----------------
    engine = TradingEngine(service=service, dry_run=dry_run)

    result = engine.run(
        stock=stock,
        quantity=getattr(settings, "DEFAULT_ORDER_QUANTITY", 1),
    )

    signal_data = result.get("signal_data", {})
    order_result = result.get("order_result", {})

    candles = signal_data.get("candles", [])

    # 🔹 CLEAN SIGNAL PANEL (NO CANDLES HERE)
    clean_signal = {
        "signal": signal_data.get("signal"),
        "timestamp": signal_data.get("timestamp"),
        "last_close": signal_data.get("last_close"),
        "ema_short": signal_data.get("ema_short"),
        "ema_long": signal_data.get("ema_long"),
        "diff": signal_data.get("diff"),
    }

    # 🔹 OHLC PREVIEW
    preview_count = len(candles)
    ohlc_preview = candles[-preview_count:] if candles else []

    # 🔹 DF DEBUG BLOCK
    df_debug = {
        "rows": len(candles),
        "columns": list(candles[0].keys()) if candles else []
    }

    # ---------------- SAFE BROKER CALLS ----------------
    try:
        margin = service.smart.rmsLimit()
    except Exception as e:
        margin = {"status": False, "error": str(e)}

    trade_state = TradeState.objects.filter(
        symbol=stock.trading_symbol
    ).first()

    login_data = {
        "status": login_resp.get("status"),
        "clientcode": login_resp.get("data", {}).get("clientcode"),
        "message": login_resp.get("message"),
        "login_time": timezone.now().isoformat()
    }

    return JsonResponse({
        "login": login_data,
        "signal": clean_signal,
        "ohlc_preview": ohlc_preview,
        "ohlc_meta": {
            "total_candles": len(candles),
            "first_timestamp": candles[0]["timestamp"] if candles else None,
            "last_timestamp": candles[-1]["timestamp"] if candles else None,
        },
        "df_debug": df_debug,
        "order_result": order_result,
        "margin": margin,
        "trade_state": {
            "position": trade_state.position if trade_state else "NONE",
            "last_signal": trade_state.last_signal if trade_state else "NONE",
        },
        "server_time": timezone.now().isoformat()
    })


# ==========================================================
# SIGNAL HISTORY PAGE
# ==========================================================
from django.utils.dateparse import parse_date

def signal_history_page(request):
    """
    Institutional Signal Monitoring Page with filters.

    Filters:
    - Stock
    - Signal type
    - Execution status
    - Date range
    """

    signals = SignalLog.objects.select_related("stock").all()

    # ------------------------------
    # Filters
    # ------------------------------

    stock_id = request.GET.get("stock")
    signal_type = request.GET.get("signal")
    executed = request.GET.get("executed")
    from_date = request.GET.get("from")
    to_date = request.GET.get("to")

    if stock_id:
        signals = signals.filter(stock_id=stock_id)

    if signal_type:
        signals = signals.filter(signal=signal_type)

    if executed == "true":
        signals = signals.filter(executed=True)
    elif executed == "false":
        signals = signals.filter(executed=False)

    if from_date:
        parsed_from = parse_date(from_date)
        if parsed_from:
            signals = signals.filter(generated_at__date__gte=parsed_from)

    if to_date:
        parsed_to = parse_date(to_date)
        if parsed_to:
            signals = signals.filter(generated_at__date__lte=parsed_to)

    signals = signals.order_by("-generated_at")[:200]

    stocks = StockConfig.objects.all()

    return render(request, "trading/signal_logs.html", {
        "signals": signals,
        "stocks": stocks,
        "filters": {
            "stock": stock_id,
            "signal": signal_type,
            "executed": executed,
            "from": from_date,
            "to": to_date,
        }
    })

# def signal_history_page(request):
#
#     signals = (
#         SignalLog.objects
#         .select_related("stock")
#         .all()
#         .order_by("-generated_at")[:100]
#     )
#
#     return render(request, "trading/signal_logs.html", {
#         "signals": signals
#     })