# options/analytics/option_metrics.py

class OptionMetrics:
    """
    Contains all analytics logic.
    No API calls.
    No Django logic.
    Pure calculation layer.
    """

    def calculate_pcr(self, df):

        total_put_oi = df["pe_oi"].sum()
        total_call_oi = df["ce_oi"].sum()

        if total_call_oi == 0:
            return 0

        return total_put_oi / total_call_oi

    def find_atm(self, df, spot_price):

        df["distance"] = abs(df["strike"] - spot_price)

        return df.loc[df["distance"].idxmin(), "strike"]

    def find_support_resistance(self, df):

        resistance = df.loc[df["ce_oi"].idxmax(), "strike"]
        support = df.loc[df["pe_oi"].idxmax(), "strike"]

        return support, resistance