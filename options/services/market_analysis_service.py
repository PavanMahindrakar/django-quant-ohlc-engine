class MarketAnalysisService:

    @staticmethod
    def generate_summary(data):

        summary = []

        spot = data.get("spot")
        pcr = data.get("pcr")
        resistance = data.get("highest_call_oi")
        support = data.get("highest_put_oi")
        strong_flows = data.get("strongFlows", [])
        chain = data.get("data", [])

        # --------------------------------------------------
        # PCR Sentiment
        # --------------------------------------------------
        if pcr:

            if pcr >= 1.2:
                summary.append(f"Strong bullish sentiment (PCR {pcr})")

            elif 1.0 <= pcr < 1.2:
                summary.append(f"Bullish sentiment (PCR {pcr})")

            elif 0.8 <= pcr < 1.0:
                summary.append(f"Slightly bearish sentiment (PCR {pcr})")

            else:
                summary.append(f"Strong bearish sentiment (PCR {pcr})")

        # --------------------------------------------------
        # Support / Resistance Logic
        # --------------------------------------------------
        if support and resistance:

            if support == resistance:
                summary.append(f"Market pinned near {support}")

            else:

                if spot < support:
                    summary.append(f"Spot trading below support {support}")

                elif spot > resistance:
                    summary.append(f"Spot trading above resistance {resistance}")

                else:
                    summary.append(f"Spot trading between {support} and {resistance}")

                summary.append(f"Key option range: {support} - {resistance}")

        # --------------------------------------------------
        # Call Wall / Put Wall Detection
        # --------------------------------------------------
        if resistance:
            summary.append(f"Call wall forming near {resistance}")

        if support:
            summary.append(f"Put wall forming near {support}")

        if support and resistance and support != resistance:
            summary.append(f"Expected option range {support} - {resistance}")

        # --------------------------------------------------
        # Call Writing / Put Writing Detection
        # --------------------------------------------------
        CALL_WRITING_THRESHOLD = 50000
        PUT_WRITING_THRESHOLD = 50000

        call_writing_strike = None
        put_writing_strike = None

        for item in chain:

            strike = item["strikePrice"]

            ce_day_change = item.get("CE", {}).get("dayOiChange", 0)
            pe_day_change = item.get("PE", {}).get("dayOiChange", 0)

            # Call writing above spot
            if strike > spot and ce_day_change > CALL_WRITING_THRESHOLD:
                call_writing_strike = strike

            # Put writing below spot
            if strike < spot and pe_day_change > PUT_WRITING_THRESHOLD:
                put_writing_strike = strike

        if call_writing_strike:
            summary.append(f"Call writers active near {call_writing_strike} resistance")

        if put_writing_strike:
            summary.append(f"Put writers defending {put_writing_strike} support")

        if call_writing_strike and spot < call_writing_strike:
            summary.append("Upside likely capped by call writers")

        # --------------------------------------------------
        # Flow Interpretation
        # --------------------------------------------------
        if strong_flows:

            top_flow = strong_flows[0]

            strike = top_flow["strike"]
            side = top_flow["side"]
            buildup = top_flow["fiveMinBuildUp"]

            if buildup == "Long Build-Up":
                summary.append(f"Fresh long positions building at {strike} {side}")

            elif buildup == "Short Build-Up":
                summary.append(f"Short positions building at {strike} {side}")

            elif buildup == "Short Covering":
                summary.append(f"Short covering observed at {strike} {side}")

            elif buildup == "Long Unwinding":
                summary.append(f"Long unwinding observed at {strike} {side}")

        else:
            summary.append("Market currently consolidating (no strong option flow)")

        return summary