from options.services.instrument_service import InstrumentService
from datetime import datetime
from options.services.greeks_service import GreeksService


class OptionChainService:
    """
    Responsible for fetching live option chain data
    and computing analytics (Greeks + OI structure).
    """

    def __init__(self, symbol: str, broker_service):
        self.symbol = symbol
        self.service = broker_service
        self.instrument_service = InstrumentService()

    # ==========================================================
    # FETCH LIVE OPTION CHAIN
    # ==========================================================

    def fetch(self, expiry: str = None, strike_window: int = 20, previous_data = None, baseline_data = None):

        # --------------------------------------------
        # 1️⃣ Load Instrument Master
        # --------------------------------------------
        instrument_df = self.instrument_service.fetch_instruments()

        # --------------------------------------------
        # 2️⃣ Fetch Spot Token (AMXIDX)
        # --------------------------------------------
        spot_row = instrument_df[
            (instrument_df["name"] == self.symbol) &
            (instrument_df["instrumenttype"] == "AMXIDX")
        ]

        if spot_row.empty:
            return {"error": "Index spot token not found"}

        spot_token = spot_row.iloc[0]["token"]

        spot_data = self.service.smart.ltpData(
            exchange="NSE",
            tradingsymbol=self.symbol,
            symboltoken=spot_token
        )

        spot = None
        if spot_data.get("status"):
            spot = spot_data["data"]["ltp"]

        if not spot:
            return {"error": "Failed to fetch spot price"}

        # --------------------------------------------
        # 3️⃣ Filter Option Contracts (OPTIDX)
        # --------------------------------------------
        contracts_df = instrument_df[
            (instrument_df["name"] == self.symbol) &
            (instrument_df["instrumenttype"] == "OPTIDX")
        ]

        if contracts_df.empty:
            return {"error": "No option contracts found"}

        # --------------------------------------------
        # 4️⃣ Determine Expiry
        # --------------------------------------------
        expiries = sorted(contracts_df["expiry"].unique())

        if not expiry:
            expiry = expiries[0]

        contracts_df = contracts_df[contracts_df["expiry"] == expiry]

        # --------------------------------------------
        # 5️⃣ Limit to ATM ± Window
        # --------------------------------------------
        contracts_df["strike"] = contracts_df["strike"].astype(float) / 100
        contracts_df["strike_diff"] = abs(contracts_df["strike"] - float(spot))
        contracts_df = contracts_df.sort_values("strike_diff")
        contracts_df = contracts_df.head(strike_window * 2)

        # --------------------------------------------
        # 6️⃣ Fetch Market Data
        # --------------------------------------------
        tokens = contracts_df["token"].tolist()

        market_response = self.service.smart.getMarketData(
            mode="FULL",
            exchangeTokens={"NFO": tokens}
        )

        if not market_response.get("status"):
            return {"error": "Failed to fetch market data"}

        market_data = market_response.get("data", {}).get("fetched", [])

        token_map = {
            str(item["symbolToken"]): item for item in market_data
        }
        # 6️⃣ Previous Snapshot Map
        previous_map = {}

        if previous_data:
            for item in previous_data:
                strike_key = round(float(item["strikePrice"]), 2)
                previous_map[strike_key] = item

        # 6️⃣.1 Baseline Snapshot Map (NEW)
        baseline_map = {}

        if baseline_data:
            for item in baseline_data:
                strike_key = round(float(item["strikePrice"]), 2)
                baseline_map[strike_key] = item
        # --------------------------------------------
        # 7️⃣ Build Option Chain + Greeks
        # --------------------------------------------
        chain = {}

        expiry_date = datetime.strptime(expiry, "%d%b%Y")
        today = datetime.now()
        days_to_expiry = (expiry_date - today).days
        T = max(days_to_expiry / 365, 0.0001)

        r = 0.06  # risk-free rate

        for _, row in contracts_df.iterrows():

            strike = float(row["strike"])
            token = str(row["token"])
            option_type = "CE" if row["symbol"].endswith("CE") else "PE"

            live = token_map.get(token, {})
            ltp = live.get("ltp", 0)
            oi = live.get("opnInterest", 0)

            # ---- Previous comparison ----
            prev_strike = previous_map.get(round(strike, 2), {})
            prev_side = prev_strike.get(option_type, {})

            prev_oi = prev_side.get("openInterest", 0)
            prev_price = prev_side.get("lastPrice", 0)

            oi_change = oi - prev_oi
            price_change = ltp - prev_price

            # --------------------------------------------------
            # ---- Day Baseline Comparison (Intraday ΔOI) ----
            # --------------------------------------------------

            day_oi_change = 0  # default

            if baseline_data:
                baseline_strike = baseline_map.get(round(strike, 2), {})
                baseline_side = baseline_strike.get(option_type, {})

                baseline_oi = baseline_side.get("openInterest", 0)

                # Intraday change = current OI - baseline OI
                day_oi_change = oi - baseline_oi

            # ---- Build-Up Classification ----
            build_up = "Neutral"

            if prev_oi > 0:  # Avoid false first-run signals
                if price_change > 0 and oi_change > 0:
                    build_up = "Long Build-Up"
                elif price_change < 0 and oi_change > 0:
                    build_up = "Short Build-Up"
                elif price_change > 0 and oi_change < 0:
                    build_up = "Short Covering"
                elif price_change < 0 and oi_change < 0:
                    build_up = "Long Unwinding"

            # ---- Greeks ----
            if ltp > 0:
                iv = GreeksService.implied_volatility(
                    spot, strike, T, r, ltp, option_type
                )
                delta = GreeksService.delta(spot, strike, T, r, iv, option_type)
                gamma = GreeksService.gamma(spot, strike, T, r, iv)
                theta = GreeksService.theta(spot, strike, T, r, iv, option_type)
                vega = GreeksService.vega(spot, strike, T, r, iv)
            else:
                iv = delta = gamma = theta = vega = 0

            if strike not in chain:
                chain[strike] = {
                    "expiry": expiry,
                    "strikePrice": strike,
                    "CE": {},
                    "PE": {},
                }

            chain[strike][option_type] = {
                "openInterest": int(oi),
                "oiChange": int(oi_change),
                "buildUp": build_up,
                "lastPrice": float(ltp),
                "iv": round(iv, 4),
                "delta": round(delta, 4),
                "gamma": round(gamma, 6),
                "theta": round(theta, 4),
                "vega": round(vega, 4),
                "dayOiChange": int(day_oi_change),
            }

        # --------------------------------------------
        # 8️⃣ OI Analytics
        # --------------------------------------------
        total_call_oi = 0
        total_put_oi = 0

        for strike_data in chain.values():
            total_call_oi += strike_data["CE"].get("openInterest", 0)
            total_put_oi += strike_data["PE"].get("openInterest", 0)

        pcr = round(total_put_oi / total_call_oi, 3) if total_call_oi else 0

        highest_call_oi_strike = max(
            chain.values(),
            key=lambda x: x["CE"].get("openInterest", 0)
        )["strikePrice"]

        highest_put_oi_strike = max(
            chain.values(),
            key=lambda x: x["PE"].get("openInterest", 0)
        )["strikePrice"]

        # --------------------------------------------
        # 9️⃣ Max Pain Calculation
        # --------------------------------------------
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

        # --------------------------------------------
        # 10️⃣ Final Return
        # --------------------------------------------
        return {
            "symbol": self.symbol,
            "spot": float(spot),
            "pcr": pcr,
            "max_pain": max_pain,
            "highest_call_oi": highest_call_oi_strike,
            "highest_put_oi": highest_put_oi_strike,
            "data": list(chain.values()),
        }