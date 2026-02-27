# options/views.py

from django.http import JsonResponse
from options.engine.option_engine import OptionEngine

from django.shortcuts import render
from trading.services.angelone_service import AngelOneService
from options.services.option_chain_service import OptionChainService
from .models import OptionChainSnapshot


def option_chain_summary(request):

    expiry = request.GET.get("expiry")

    engine = OptionEngine(symbol="NIFTY")
    result = engine.run(expiry=expiry)

    return JsonResponse(result)

def option_strike_detail(request):

    expiry = request.GET.get("expiry")
    strike = request.GET.get("strike")

    if not expiry or not strike:
        return JsonResponse(
            {"error": "expiry and strike are required"},
            status=400
        )

    engine = OptionEngine(symbol="NIFTY")

    result = engine.strike_details(
        expiry=expiry,
        strike=int(strike)
    )

    return JsonResponse(result)

def option_chain_view(request):
    service = AngelOneService()
    service.login()

    # 1️⃣ Get latest snapshot for SAME symbol
    previous_snapshot = OptionChainSnapshot.objects.filter(
        symbol="NIFTY"
    ).order_by("-created_at").first()

    previous_data = previous_snapshot.raw_data if previous_snapshot else None

    # 2️⃣ Fetch new data and pass previous snapshot
    option_service = OptionChainService("NIFTY", service)
    data = option_service.fetch(previous_data=previous_data)

    if "error" in data:
        return render(request, "options/error.html", {"error": data["error"]})

    # 3️⃣ Save NEW snapshot AFTER comparison
    snapshot = OptionChainSnapshot.objects.create(
        symbol=data["symbol"],
        expiry=data["data"][0]["expiry"],
        spot=data["spot"],
        raw_data=data["data"]
    )

    context = {
        "spot": data["spot"],
        "symbol": data["symbol"],
        "expiry": data["data"][0]["expiry"],
        "chain": data["data"],
        "timestamp": snapshot.created_at,
        "pcr": data.get("pcr"),
        "max_pain": data.get("max_pain"),
        "highest_call_oi": data.get("highest_call_oi"),
        "highest_put_oi": data.get("highest_put_oi"),
    }

    return render(request, "options/option_chain.html", context)
