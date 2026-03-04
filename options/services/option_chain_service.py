from options.services.instrument_service import InstrumentService
from datetime import datetime
from options.services.greeks_service import GreeksService


# --------------------------------------------------
# 🔵 NEW: Flow Quality Filters
# --------------------------------------------------
MIN_OI_FILTER = 1000
FLOW_THRESHOLD = 100000
STRIKE_DISTANCE_LIMIT = 700


class OptionChainService:

    def __init__(self, symbol: str, broker_service):
        self.symbol = symbol
        self.service = broker_service
        self.instrument_service = InstrumentService()

    def fetch(
        self,
        expiry: str = None,
        strike_window: int = 20,
        previous_data=None,
        baseline_data=None,
        recent_data_list=None,
        five_min_data=None,
    ):

        instrument_df = self.instrument_service.fetch_instruments()

        # --------------------------------------------------
        # Spot Fetch
        # --------------------------------------------------
        spot_row = instrument_df[
            (instrument_df["name"] == self.symbol)
            & (instrument_df["instrumenttype"] == "AMXIDX")
        ]

        if spot_row.empty:
            return {"error": "Index spot token not found"}

        spot_token = spot_row.iloc[0]["token"]

        spot_data = self.service.smart.ltpData(
            exchange="NSE",
            tradingsymbol=self.symbol,
            symboltoken=spot_token,
        )

        if not spot_data.get("status"):
            return {"error": "Failed to fetch spot price"}

        spot = spot_data["data"]["ltp"]

        # --------------------------------------------------
        # Contracts
        # --------------------------------------------------
        contracts_df = instrument_df[
            (instrument_df["name"] == self.symbol)
            & (instrument_df["instrumenttype"] == "OPTIDX")
        ]

        if contracts_df.empty:
            return {"error": "No option contracts found"}

        expiries = sorted(contracts_df["expiry"].unique())
        if not expiry:
            expiry = expiries[0]

        contracts_df = contracts_df[contracts_df["expiry"] == expiry]

        contracts_df["strike"] = contracts_df["strike"].astype(float) / 100
        contracts_df["strike_diff"] = abs(
            contracts_df["strike"] - float(spot)
        )
        contracts_df = contracts_df.sort_values("strike_diff")
        contracts_df = contracts_df.head(strike_window * 2)

        # --------------------------------------------------
        # Market Data
        # --------------------------------------------------
        tokens = contracts_df["token"].tolist()

        market_response = self.service.smart.getMarketData(
            mode="FULL", exchangeTokens={"NFO": tokens}
        )

        if not market_response.get("status"):
            return {"error": "Failed to fetch market data"}

        market_data = market_response.get("data", {}).get("fetched", [])

        token_map = {
            str(item["symbolToken"]): item for item in market_data
        }

        # --------------------------------------------------
        # Snapshot Maps
        # --------------------------------------------------
        previous_map = {}
        if previous_data:
            for item in previous_data:
                previous_map[
                    round(float(item["strikePrice"]), 2)
                ] = item

        baseline_map = {}
        if baseline_data:
            for item in baseline_data:
                baseline_map[
                    round(float(item["strikePrice"]), 2)
                ] = item

        five_min_map = {}
        if five_min_data:
            for item in five_min_data:
                five_min_map[
                    round(float(item["strikePrice"]), 2)
                ] = item

        # --------------------------------------------------
        # 🔵 NEW: Recent Snapshots Map (Acceleration)
        # --------------------------------------------------
        recent_map = {}

        if recent_data_list:
            for snapshot_data in recent_data_list:
                for item in snapshot_data:
                    strike_key = round(float(item["strikePrice"]), 2)

                    if strike_key not in recent_map:
                        recent_map[strike_key] = {"CE": [], "PE": []}

                    for side in ["CE", "PE"]:
                        oi_val = item.get(side, {}).get("openInterest", 0)
                        recent_map[strike_key][side].append(oi_val)

        # --------------------------------------------------
        # Build Chain
        # --------------------------------------------------
        chain = {}

        expiry_date = datetime.strptime(expiry, "%d%b%Y")
        days_to_expiry = (expiry_date - datetime.now()).days
        T = max(days_to_expiry / 365, 0.0001)
        r = 0.06

        for _, row in contracts_df.iterrows():

            strike = float(row["strike"])

            # 🔵 NEW: Ignore far OTM strikes
            if abs(strike - spot) > STRIKE_DISTANCE_LIMIT:
                continue

            strike_key = round(strike, 2)
            token = str(row["token"])
            option_type = (
                "CE" if row["symbol"].endswith("CE") else "PE"
            )

            live = token_map.get(token, {})
            ltp = float(live.get("ltp", 0) or 0)
            oi = int(live.get("opnInterest", 0) or 0)

            # 🔵 NEW: Ignore illiquid strikes
            # if oi < MIN_OI_FILTER:
            #     continue

            # Previous
            prev_side = previous_map.get(strike_key, {}).get(option_type, {})
            prev_oi = prev_side.get("openInterest", 0)
            prev_price = prev_side.get("lastPrice", 0)

            oi_change = oi - prev_oi
            price_change = ltp - prev_price

            # Baseline
            day_oi_change = 0
            if baseline_data:
                baseline_side = baseline_map.get(strike_key, {}).get(option_type, {})
                baseline_oi = baseline_side.get("openInterest", 0)
                day_oi_change = oi - baseline_oi

            # 5-Min
            five_min_oi_change = 0
            five_min_build_up = "Neutral"

            if five_min_data and strike_key in five_min_map:

                five_min_side = five_min_map.get(strike_key, {}).get(option_type, {})

                five_min_oi = five_min_side.get("openInterest", 0) or 0
                five_min_price = five_min_side.get("lastPrice", 0) or 0

                five_min_oi_change = oi - five_min_oi
                five_min_price_change = ltp - float(five_min_price)

                if five_min_oi > 0:
                    if five_min_price_change > 0 and five_min_oi_change > 0:
                        five_min_build_up = "Long Build-Up"
                    elif five_min_price_change < 0 and five_min_oi_change > 0:
                        five_min_build_up = "Short Build-Up"
                    elif five_min_price_change > 0 and five_min_oi_change < 0:
                        five_min_build_up = "Short Covering"
                    elif five_min_price_change < 0 and five_min_oi_change < 0:
                        five_min_build_up = "Long Unwinding"

            # Tick Build
            build_up = "Neutral"
            if prev_oi > 0 and previous_data:
                if price_change > 0 and oi_change > 0:
                    build_up = "Long Build-Up"
                elif price_change < 0 and oi_change > 0:
                    build_up = "Short Build-Up"
                elif price_change > 0 and oi_change < 0:
                    build_up = "Short Covering"
                elif price_change < 0 and oi_change < 0:
                    build_up = "Long Unwinding"

            # --------------------------------------------------
            # 🔵 NEW: Acceleration Detection (Phase 3.2)
            # --------------------------------------------------
            acceleration = "Normal"

            ACCEL_MULTIPLIER = 3
            MIN_OI_THRESHOLD = 50000

            if recent_data_list and strike_key in recent_map:

                history = recent_map[strike_key][option_type]

                if len(history) >= 3:

                    deltas = [
                        abs(history[i] - history[i - 1])
                        for i in range(1, len(history))
                    ]

                    if deltas:
                        avg_delta = sum(deltas) / len(deltas)

                        if (
                            avg_delta > 0
                            and abs(oi_change) > MIN_OI_THRESHOLD
                            and abs(oi_change) > ACCEL_MULTIPLIER * avg_delta
                        ):
                            acceleration = "ACCEL ↑" if oi_change > 0 else "ACCEL ↓"

            # Greeks
            iv = delta = gamma = theta = vega = 0

            if ltp > 0.5:
                iv = GreeksService.implied_volatility(
                    spot, strike, T, r, ltp, option_type
                )
                if 0 < iv <= 5:
                    delta = GreeksService.delta(spot, strike, T, r, iv, option_type)
                    gamma = GreeksService.gamma(spot, strike, T, r, iv)
                    theta = GreeksService.theta(spot, strike, T, r, iv, option_type)
                    vega = GreeksService.vega(spot, strike, T, r, iv)
                else:
                    iv = 0

            if strike not in chain:
                chain[strike] = {
                    "expiry": expiry,
                    "strikePrice": strike,
                    "CE": {},
                    "PE": {},
                }

            chain[strike][option_type] = {
                "openInterest": oi,
                "oiChange": oi_change,
                "dayOiChange": day_oi_change,
                "fiveMinOiChange": five_min_oi_change,
                "buildUp": build_up,
                "fiveMinBuildUp": five_min_build_up,
                "acceleration": acceleration,
                "lastPrice": ltp,
                "iv": round(iv, 4),
                "delta": round(delta, 4),
                "gamma": round(gamma, 6),
                "theta": round(theta, 4),
                "vega": round(vega, 4),
            }

        # --------------------------------------------------
        # Analytics Restored
        # --------------------------------------------------
        total_call_oi = sum(
            x["CE"].get("openInterest", 0)
            for x in chain.values()
        )

        total_put_oi = sum(
            x["PE"].get("openInterest", 0)
            for x in chain.values()
        )

        pcr = round(total_put_oi / total_call_oi, 3) if total_call_oi else 0

        highest_call_oi_strike = max(
            chain.values(),
            key=lambda x: x["CE"].get("openInterest", 0),
        )["strikePrice"]

        highest_put_oi_strike = max(
            chain.values(),
            key=lambda x: x["PE"].get("openInterest", 0),
        )["strikePrice"]

        max_pain = None
        min_pain_value = float("inf")

        for strike_i in chain.values():
            strike_price = strike_i["strikePrice"]
            pain = 0

            for strike_j in chain.values():
                strike_j_price = strike_j["strikePrice"]
                call_oi = strike_j["CE"].get("openInterest", 0)
                put_oi = strike_j["PE"].get("openInterest", 0)

                if strike_j_price > strike_price:
                    pain += (strike_j_price - strike_price) * call_oi
                if strike_j_price < strike_price:
                    pain += (strike_price - strike_j_price) * put_oi

            if pain < min_pain_value:
                min_pain_value = pain
                max_pain = strike_price

        # --------------------------------------------------
        # Strongest 5-Min Flow
        # --------------------------------------------------
        strong_flows = []

        for strike_data in chain.values():
            for side in ["CE", "PE"]:
                side_data = strike_data.get(side, {})
                change = side_data.get("fiveMinOiChange", 0)

                if abs(change) > FLOW_THRESHOLD:
                    strong_flows.append({
                        "strike": strike_data["strikePrice"],
                        "side": side,
                        "fiveMinOiChange": change,
                        "fiveMinBuildUp": side_data.get("fiveMinBuildUp", "Neutral")
                    })

        strong_flows = sorted(
            strong_flows,
            key=lambda x: abs(x["fiveMinOiChange"]),
            reverse=True
        )[:5]

        return {
            "symbol": self.symbol,
            "spot": float(spot),
            "pcr": pcr,
            "max_pain": max_pain,
            "highest_call_oi": highest_call_oi_strike,
            "highest_put_oi": highest_put_oi_strike,
            "data": list(chain.values()),
            "strongFlows": strong_flows,
        }