from SmartApi import SmartConnect
import pyotp
from django.conf import settings
from datetime import datetime, timedelta


class AngelOneService:
    """
    Handles:
    - SmartAPI login
    - Fetching recent candle data
    """

    def __init__(self):
        self.api_key = settings.SMARTAPI_API_KEY
        self.client_id = settings.SMARTAPI_CLIENT_ID
        self.username = settings.SMARTAPI_USERNAME
        self.password = settings.SMARTAPI_PASSWORD
        self.totp_secret = settings.SMARTAPI_TOTP_SECRET

        self.smart = None

    def login(self):
        """
        Login using SmartAPI SDK.
        """

        if not all([
            self.api_key,
            self.username,
            self.password,
            self.totp_secret
        ]):
            raise ValueError("SmartAPI credentials missing in .env")

        try:
            totp = pyotp.TOTP(self.totp_secret).now()

            self.smart = SmartConnect(api_key=self.api_key)

            session = self.smart.generateSession(
                self.username,
                self.password,
                totp
            )

            if not session.get("status"):
                raise Exception(f"Login failed: {session}")

            return session

        except Exception as e:
            raise Exception(f"SmartAPI Login Error: {str(e)}")

    def fetch_recent_candles(self, symbol_token, interval="ONE_MINUTE", n=100):
        """
        Fetch last N candles safely.
        """

        if not self.smart:
            raise Exception("Login must be called before fetching candles")

        try:
            to_date = datetime.now()
            from_date = to_date - timedelta(days=5)

            params = {
                "exchange": "NSE",
                "symboltoken": symbol_token,
                "interval": interval,
                "fromdate": from_date.strftime("%Y-%m-%d %H:%M"),
                "todate": to_date.strftime("%Y-%m-%d %H:%M"),
            }

            response = self.smart.getCandleData(params)

            if not response.get("status"):
                raise Exception(f"Candle fetch failed: {response}")

            data = response.get("data")

            if not data:
                raise Exception("Empty candle data received")

            return data[-n:]  # Last N candles

        except Exception as e:
            raise Exception(f"Candle Fetch Error: {str(e)}")


#
# class AngelOneAuthService:
#     """
#     Handles authentication with Angel One SmartAPI.
#     Only responsible for login/session generation.
#     """
#
#     def __init__(self):
#         self.api_key = settings.TRADING_API_KEY
#         self.client_code = settings.TRADING_CLIENT_CODE
#         self.secret_key = settings.TRADING_API_SECRET
#         self.base_url = settings.TRADING_BASE_URL
#
#     def login(self, password: str) -> dict:
#         """
#         Perform login to SmartAPI and return response data.
#
#         :param password: User trading account password
#         :return: dict containing authentication response
#         """
#
#         if not all([self.api_key, self.client_code, self.secret_key]):
#             raise ValueError("Trading API credentials are not configured properly.")
#
#         login_endpoint = f"{self.base_url}/login"
#
#         payload = {
#             "api_key": self.api_key,
#             "client_code": self.client_code,
#             "password": password,
#         }
#
#         try:
#             response = requests.post(login_endpoint, json=payload, timeout=10)
#
#             if response.status_code != 200:
#                 raise Exception(f"Authentication failed: {response.text}")
#
#             return response.json()
#
#         except requests.exceptions.RequestException as e:
#             raise Exception(f"Network error during authentication: {str(e)}")
#
#
#     def get_ohlc(self, symbol: str, exchange: str, timeframe: str) -> dict:
#         """
#         Fetch OHLC data from Angel One SmartAPI.
#
#         :param symbol: Trading symbol (e.g., RELIANCE)
#         :param exchange: Exchange code (e.g., NSE)
#         :param timeframe: Candle interval (e.g., ONE_MINUTE)
#         :return: Raw OHLC response JSON
#         """
#
#         if not self.base_url:
#             raise ValueError("Trading base URL is not configured.")
#
#         ohlc_endpoint = f"{self.base_url}/marketdata/ohlc"
#
#         payload = {
#             "symbol": symbol,
#             "exchange": exchange,
#             "interval": timeframe
#         }
#
#         try:
#             response = requests.post(ohlc_endpoint, json=payload, timeout=10)
#
#             if response.status_code != 200:
#                 raise Exception(f"Failed to fetch OHLC data: {response.text}")
#
#             return response.json()
#
#         except requests.exceptions.RequestException as e:
#             raise Exception(f"Network error while fetching OHLC: {str(e)}")
#
