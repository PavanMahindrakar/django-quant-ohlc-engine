import math
from scipy.stats import norm


class GreeksCalculator:

    def __init__(self, spot, strike, time_to_expiry, rate, volatility):
        self.S = spot
        self.K = strike
        self.T = time_to_expiry
        self.r = rate
        self.sigma = volatility

    def _d1(self):
        return (
            math.log(self.S / self.K)
            + (self.r + 0.5 * self.sigma ** 2) * self.T
        ) / (self.sigma * math.sqrt(self.T))

    def _d2(self):
        return self._d1() - self.sigma * math.sqrt(self.T)

    def call_greeks(self):
        d1 = self._d1()
        d2 = self._d2()

        delta = norm.cdf(d1)
        gamma = norm.pdf(d1) / (
            self.S * self.sigma * math.sqrt(self.T)
        )
        theta = (
            - (self.S * norm.pdf(d1) * self.sigma) /
            (2 * math.sqrt(self.T))
            - self.r * self.K * math.exp(-self.r * self.T) * norm.cdf(d2)
        )
        theta = theta / 365
        vega = self.S * norm.pdf(d1) * math.sqrt(self.T)

        return {
            "delta": float(round(delta, 4)),
            "gamma": float(round(gamma, 6)),
            "theta": float(round(theta, 4)),
            "vega": float(round(vega, 4)),
        }

    def put_greeks(self):
        d1 = self._d1()
        d2 = self._d2()

        delta = norm.cdf(d1) - 1
        gamma = norm.pdf(d1) / (
            self.S * self.sigma * math.sqrt(self.T)
        )
        theta = (
            - (self.S * norm.pdf(d1) * self.sigma) /
            (2 * math.sqrt(self.T))
            + self.r * self.K * math.exp(-self.r * self.T) * norm.cdf(-d2)
        )
        theta = theta / 365  #covert to daily theta
        vega = self.S * norm.pdf(d1) * math.sqrt(self.T)

        return {
            "delta": float(round(delta, 4)),
            "gamma": float(round(gamma, 6)),
            "theta": float(round(theta, 4)),
            "vega": float(round(vega, 4)),
        }