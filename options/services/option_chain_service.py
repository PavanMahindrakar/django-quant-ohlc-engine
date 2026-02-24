# options/services/option_chain_service.py

from options.services.instrument_service import InstrumentService


class OptionChainService:
    """
    Responsible ONLY for fetching raw option chain data.
    No transformation or analytics logic here.
    """

    def __init__(self, symbol: str, broker_service):
        self.symbol = symbol
        self.service = broker_service
        self.instrument_service = InstrumentService()

    # ==========================================================
    # FETCH LIVE OPTION CHAIN
    # ==========================================================

    def fetch(self, expiry: str = None, strike_window: int = 20):
        """
        strike_window:
            Number of strikes around ATM (CE+PE pairs)
        """

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
        # 5️⃣ Limit to ATM ± Window (Prevent API Overload)
        # --------------------------------------------
        contracts_df["strike"] = contracts_df["strike"].astype(float)
        contracts_df["strike_diff"] = abs(contracts_df["strike"] - float(spot))

        contracts_df = contracts_df.sort_values("strike_diff")

        # Take limited strikes (each strike has CE + PE)
        contracts_df = contracts_df.head(strike_window * 2)

        # --------------------------------------------
        # 6️⃣ Prepare Market Data Request (NFO)
        # --------------------------------------------
        tokens = contracts_df["token"].tolist()

        exchange_tokens = {
            "NFO": tokens
        }

        market_response = self.service.smart.getMarketData(
            mode="FULL",
            exchangeTokens=exchange_tokens
        )

        if not market_response.get("status"):
            return {"error": "Failed to fetch market data"}

        market_data = market_response.get("data", {}).get("fetched",[])
        # print("RAW Market Response:", market_response)
        # return {"debug": market_response}
        # --------------------------------------------
        # 7️⃣ Map token → market data
        # --------------------------------------------
        token_map = {
            item["symbolToken"]: item for item in market_data
        }

        # --------------------------------------------
        # 8️⃣ Build Structured Chain
        # --------------------------------------------
        chain = {}

        for _, row in contracts_df.iterrows():

            strike = float(row["strike"]) / 100
            token = row["token"]
            # option_type = row["symbol"][-2:]  # CE or PE
            option_type = "CE" if row["symbol"].endswith("CE") else "PE"
            live = token_map.get(str(token), {})

            ltp = live.get("ltp", 0)
            oi = live.get("openInterest", 0)

            if strike not in chain:
                chain[strike] = {
                    "expiry": expiry,
                    "strikePrice": strike,
                    "CE": {},
                    "PE": {},
                }

            chain[strike][option_type] = {
                "openInterest": int(oi),
                "lastPrice": float(ltp),
            }

        return {
            "symbol": self.symbol,
            "spot": float(spot),
            "data": list(chain.values()),
        }