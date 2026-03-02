from django.http import JsonResponse
from options.engine.option_engine import OptionEngine
from django.shortcuts import render, redirect
from trading.services.angelone_service import AngelOneService
from options.services.option_chain_service import OptionChainService
from .models import OptionChainSnapshot
from django.utils import timezone
from datetime import timedelta


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

    # --------------------------------------------------
    # Detect Current Expiry from Latest Snapshot
    # --------------------------------------------------
    latest_snapshot = OptionChainSnapshot.objects.filter(
        symbol="NIFTY"
    ).order_by("-created_at").first()

    current_expiry = latest_snapshot.expiry if latest_snapshot else None

    # --------------------------------------------------
    # Load Snapshots (Expiry-safe)
    # --------------------------------------------------
    if current_expiry:
        snapshots = OptionChainSnapshot.objects.filter(
            symbol="NIFTY",
            expiry=current_expiry
        ).order_by("-created_at")
    else:
        snapshots = OptionChainSnapshot.objects.filter(
            symbol="NIFTY"
        ).order_by("-created_at")

    previous_snapshot = snapshots.first()
    previous_data = previous_snapshot.raw_data if previous_snapshot else None

    # --------------------------------------------------
    # 5-Min Snapshot Logic
    # --------------------------------------------------
    five_min_ago = timezone.now() - timedelta(minutes=5)

    snapshot_5m = snapshots.filter(
        created_at__lte=five_min_ago
    ).order_by("-created_at").first()

    snapshot_5m_data = snapshot_5m.raw_data if snapshot_5m else None

    # --------------------------------------------------
    # Last 5 Snapshots (Acceleration)
    # --------------------------------------------------
    recent_snapshots = snapshots[1:6]
    recent_data_list = [snap.raw_data for snap in recent_snapshots]

    # --------------------------------------------------
    # Load Day Baseline (Expiry + Today Safe)
    # --------------------------------------------------
    today = timezone.now().date()

    baseline_snapshot = OptionChainSnapshot.objects.filter(
        symbol="NIFTY",
        expiry=current_expiry,
        is_day_baseline=True,
        created_at__date=today
    ).first()

    baseline_data = baseline_snapshot.raw_data if baseline_snapshot else None

    # --------------------------------------------------
    # Fetch Live Option Chain
    # --------------------------------------------------
    option_service = OptionChainService("NIFTY", service)

    data = option_service.fetch(
        previous_data=previous_data,
        baseline_data=baseline_data,
        recent_data_list=recent_data_list,
        five_min_data=snapshot_5m_data,
    )

    if "error" in data:
        return render(request, "options/error.html", {"error": data["error"]})

    # --------------------------------------------------
    # Save New Snapshot
    # --------------------------------------------------
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
        "snapshot_id": snapshot.id,
        "pcr": data.get("pcr"),
        "max_pain": data.get("max_pain"),
        "highest_call_oi": data.get("highest_call_oi"),
        "highest_put_oi": data.get("highest_put_oi"),
        "strong_flows": data.get("strongFlows", []),
    }

    return render(request, "options/option_chain.html", context)


# --------------------------------------------------
# Set Day Baseline (Expiry Safe)
# --------------------------------------------------
def set_day_baseline(request, snapshot_id):

    snapshot = OptionChainSnapshot.objects.get(id=snapshot_id)

    # Clear baseline only for same expiry
    OptionChainSnapshot.objects.filter(
        symbol="NIFTY",
        expiry=snapshot.expiry
    ).update(is_day_baseline=False)

    snapshot.is_day_baseline = True
    snapshot.save()

    return redirect("option-chain")