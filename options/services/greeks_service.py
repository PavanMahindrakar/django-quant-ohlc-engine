import math
from scipy.stats import norm


class GreeksService:

    @staticmethod
    def _d1(S, K, T, r, sigma):
        return (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))

    @staticmethod
    def _d2(d1, sigma, T):
        return d1 - sigma * math.sqrt(T)

    # -------------------------------
    # Black-Scholes Price
    # -------------------------------
    @staticmethod
    def black_scholes_price(S, K, T, r, sigma, option_type):
        d1 = GreeksService._d1(S, K, T, r, sigma)
        d2 = GreeksService._d2(d1, sigma, T)

        if option_type == "CE":
            return S * norm.cdf(d1) - K * math.exp(-r * T) * norm.cdf(d2)
        else:
            return K * math.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)

    # -------------------------------
    # Vega
    # -------------------------------
    @staticmethod
    def vega(S, K, T, r, sigma):
        d1 = GreeksService._d1(S, K, T, r, sigma)
        return S * norm.pdf(d1) * math.sqrt(T)

    # -------------------------------
    # Implied Volatility (Newton-Raphson)
    # -------------------------------
    @staticmethod
    def implied_volatility(S, K, T, r, market_price, option_type):

        if market_price <= 0:
            return 0

        sigma = 0.2  # initial guess

        for _ in range(100):
            price = GreeksService.black_scholes_price(S, K, T, r, sigma, option_type)
            vega = GreeksService.vega(S, K, T, r, sigma)

            if abs(vega) < 1e-8:
                break

            diff = price - market_price

            if abs(diff) < 1e-6:
                break

            sigma = sigma - diff / vega

            if sigma <= 0:
                sigma = 0.0001

        return sigma

    # -------------------------------
    # Delta
    # -------------------------------
    @staticmethod
    def delta(S, K, T, r, sigma, option_type):
        d1 = GreeksService._d1(S, K, T, r, sigma)

        if option_type == "CE":
            return norm.cdf(d1)
        else:
            return norm.cdf(d1) - 1

    # -------------------------------
    # Gamma
    # -------------------------------
    @staticmethod
    def gamma(S, K, T, r, sigma):
        d1 = GreeksService._d1(S, K, T, r, sigma)
        return norm.pdf(d1) / (S * sigma * math.sqrt(T))

    # -------------------------------
    # Theta (DAILY)
    # -------------------------------
    @staticmethod
    def theta(S, K, T, r, sigma, option_type):

        d1 = GreeksService._d1(S, K, T, r, sigma)
        d2 = GreeksService._d2(d1, sigma, T)

        term1 = -(S * norm.pdf(d1) * sigma) / (2 * math.sqrt(T))

        if option_type == "CE":
            theta_annual = term1 - r * K * math.exp(-r * T) * norm.cdf(d2)
        else:
            theta_annual = term1 + r * K * math.exp(-r * T) * norm.cdf(-d2)

        # Convert annual theta → daily theta
        return theta_annual / 365