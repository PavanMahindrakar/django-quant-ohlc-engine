from django.shortcuts import render
# options/views.py

from django.http import JsonResponse
from options.engine.option_engine import OptionEngine


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

