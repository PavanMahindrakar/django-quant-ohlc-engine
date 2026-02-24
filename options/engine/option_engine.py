# options/engine/option_engine.py

from options.services.option_chain_service import OptionChainService
from options.processors.option_chain_processor import OptionChainProcessor
from options.analytics.option_metrics import OptionMetrics
from options.metrics.greeks_calculator import GreeksCalculator


class OptionEngine:
    """
    Orchestrates the entire option chain flow.
    """

    def __init__(self, symbol: str):
        self.symbol = symbol

        self.service = OptionChainService(symbol)
        self.processor = OptionChainProcessor()
        self.metrics = OptionMetrics()

    # ==========================================================
    # SUMMARY ENDPOINT
    # ==========================================================

    def run(self, expiry=None):
        raw_data = self.service.fetch()

        expiries = sorted(
            list(set([item["expiry"] for item in raw_data["data"]]))
        )

        if not expiry:
            expiry = expiries[0]

        filtered_data = [
            item for item in raw_data["data"]
            if item["expiry"] == expiry
        ]

        spot = raw_data["spot"]

        df = self.processor.transform(filtered_data)

        pcr = self.metrics.calculate_pcr(df)
        atm = self.metrics.find_atm(df, spot)
        support, resistance = self.metrics.find_support_resistance(df)

        return {
            "symbol": self.symbol,
            "spot": int(spot),
            "selected_expiry": expiry,
            "available_expiries": expiries,
            "atm_strike": int(atm),
            "pcr": float(round(pcr, 2)),
            "support": int(support),
            "resistance": int(resistance),
        }

    # ==========================================================
    # STRIKE DETAIL + GREEKS
    # ==========================================================

    def strike_details(self, expiry: str, strike: int):

        raw_data = self.service.fetch()

        # Filter by expiry
        filtered = [
            item for item in raw_data["data"]
            if item["expiry"] == expiry
        ]

        # Find specific strike
        strike_data = next(
            (item for item in filtered if item["strikePrice"] == strike),
            None
        )

        if not strike_data:
            return {"error": "Strike not found for selected expiry"}

        spot = raw_data["spot"]

        ce_oi = strike_data["CE"]["openInterest"]
        pe_oi = strike_data["PE"]["openInterest"]

        ce_ltp = strike_data["CE"]["lastPrice"]
        pe_ltp = strike_data["PE"]["lastPrice"]

        oi_diff = pe_oi - ce_oi

        # Bias Logic
        if oi_diff > 0:
            bias = "PUT_WRITING"
        elif oi_diff < 0:
            bias = "CALL_WRITING"
        else:
            bias = "BALANCED"

        # ======================================================
        # Greeks Calculation (Black-Scholes Approximation)
        # ======================================================

        # Dummy assumptions (we'll improve later)
        time_to_expiry = 7 / 365
        risk_free_rate = 0.06
        implied_vol = 0.18

        calc = GreeksCalculator(
            spot=spot,
            strike=strike,
            time_to_expiry=time_to_expiry,
            rate=risk_free_rate,
            volatility=implied_vol
        )

        ce_greeks = calc.call_greeks()
        pe_greeks = calc.put_greeks()

        # ======================================================
        # Net Straddle Greeks
        # ======================================================

        net_delta = ce_greeks["delta"] + pe_greeks["delta"]
        net_gamma = ce_greeks["gamma"] + pe_greeks["gamma"]
        net_theta = ce_greeks["theta"] + pe_greeks["theta"]
        net_vega = ce_greeks["vega"] + pe_greeks["vega"]

        straddle_profile = {
            "net_delta": round(net_delta, 4),
            "net_gamma": round(net_gamma, 6),
            "net_theta": round(net_theta, 4),
            "net_vega": round(net_vega, 4),
        }

        # ======================================================
        # Strategy Intelligence Layer
        # ======================================================

        delta_neutral = abs(net_delta) < 0.05

        if delta_neutral:
            delta_bias = "DELTA_NEUTRAL"
        elif net_delta > 0:
            delta_bias = "BULLISH_TILT"
        else:
            delta_bias = "BEARISH_TILT"

        # Volatility classification
        if net_gamma > 0:
            volatility_exposure = "LONG_VOLATILITY"
        else:
            volatility_exposure = "SHORT_VOLATILITY"

        # Time decay classification
        if net_theta < 0:
            decay_profile = "TIME_DECAY_NEGATIVE"
        else:
            decay_profile = "TIME_DECAY_POSITIVE"

        strategy_profile = {
            "delta_neutral": delta_neutral,
            "delta_bias": delta_bias,
            "volatility_exposure": volatility_exposure,
            "decay_profile": decay_profile,
        }

        # ======================================================
        # Break-even & Payoff Modelling (Long Straddle)
        # ======================================================

        total_premium = ce_ltp + pe_ltp

        upper_breakeven = strike + total_premium
        lower_breakeven = strike - total_premium

        movement_required = (
                                    abs(upper_breakeven - spot) / spot
                            ) * 100

        payoff_profile = {
            "total_premium_paid": round(total_premium, 2),
            "upper_breakeven": round(upper_breakeven, 2),
            "lower_breakeven": round(lower_breakeven, 2),
            "movement_required_percent": round(movement_required, 2),
            "max_loss": round(total_premium, 2),
            "max_profit": "UNLIMITED",
        }

        # ======================================================
        # Short Straddle Modelling
        # ======================================================

        short_straddle_profile = {
            "total_premium_collected": round(total_premium, 2),
            "upper_breakeven": round(upper_breakeven, 2),
            "lower_breakeven": round(lower_breakeven, 2),
            "movement_allowed_percent": round(
                (abs(upper_breakeven - spot) / spot) * 100, 2
            ),
            "max_profit": round(total_premium, 2),
            "max_loss": "UNLIMITED",
            "volatility_exposure": "SHORT_VOLATILITY",
            "decay_profile": "TIME_DECAY_POSITIVE",
        }

        return {
            "symbol": self.symbol,
            "expiry": expiry,
            "strike": strike,
            "spot": int(spot),

            "ce_oi": int(ce_oi),
            "pe_oi": int(pe_oi),

            "ce_ltp": float(ce_ltp),
            "pe_ltp": float(pe_ltp),

            "oi_difference": int(oi_diff),
            "bias": bias,

            "ce_greeks": ce_greeks,
            "pe_greeks": pe_greeks,
            "straddle_greeks": straddle_profile,
            "strategy_profile": strategy_profile,
            "payoff_profile": payoff_profile,
            "short_straddle_profile": short_straddle_profile,
        }