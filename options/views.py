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

    option_service = OptionChainService("NIFTY", service)
    data = option_service.fetch()

    if "error" in data:
        return render(request, "options/error.html", {"error": data["error"]})

    # Save snapshot
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
    }

    return render(request, "options/option_chain.html", context)

