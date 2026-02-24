# options/processors/option_chain_processor.py

import pandas as pd

class OptionChainProcessor:

    def transform(self, strike_list):
        """
        strike_list → List of option strike dictionaries
        """

        records = []

        for item in strike_list:
            records.append({
                "strike": item["strikePrice"],
                "ce_oi": item["CE"]["openInterest"],
                "pe_oi": item["PE"]["openInterest"],
                "ce_ltp": item["CE"]["lastPrice"],
                "pe_ltp": item["PE"]["lastPrice"],
            })

        return pd.DataFrame(records)