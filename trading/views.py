# config/trading/views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse

from trading.engine.ema_pipeline import run_ema_pipeline
from .models import StockConfig
from .forms import StockConfigForm


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
    Debug endpoint:
    Returns full EMA calculation details as JSON.
    """

    result = run_ema_pipeline(
        symbol_token=symbol_token,
        interval="ONE_MINUTE",
        candle_count=100,
    )

    return JsonResponse(result)
