import requests
import pandas as pd


class InstrumentService:

    INSTRUMENT_URL = (
        "https://margincalculator.angelbroking.com/"
        "OpenAPI_File/files/OpenAPIScripMaster.json"
    )

    def fetch_instruments(self):
        response = requests.get(self.INSTRUMENT_URL)
        data = response.json()
        df = pd.DataFrame(data)
        return df

    def get_option_contracts(self, symbol="NIFTY"):
        df = self.fetch_instruments()

        # Filter only index options
        df = df[
            (df["name"] == symbol) &
            (df["instrumenttype"] == "OPTIDX")
        ]

        return df