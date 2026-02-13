"""
AngelOneService
---------------

This service is responsible ONLY for:

1. Authenticating with AngelOne SmartAPI
2. Fetching historical OHLC candle data

It does NOT:
- Run strategy
- Handle caching
- Place orders

That separation keeps architecture clean and maintainable.
"""

from SmartApi import SmartConnect
import pyotp
from django.conf import settings
from datetime import datetime, timedelta


class AngelOneService:
    """
    Wrapper around AngelOne SmartAPI SDK.

    Responsibilities:
    -----------------
    - Login using credentials stored in environment variables
    - Maintain SmartConnect object
    - Fetch recent candle data

    This class is intentionally minimal and focused.
    """

    def __init__(self):
        """
        Load credentials from Django settings (.env-backed).
        Initialize SDK object placeholder.
        """

        # 🔐 Environment-based credentials
        self.api_key = settings.SMARTAPI_API_KEY
        self.client_id = settings.SMARTAPI_CLIENT_ID
        self.username = settings.SMARTAPI_USERNAME
        self.password = settings.SMARTAPI_PASSWORD
        self.totp_secret = settings.SMARTAPI_TOTP_SECRET

        # Will hold JWT after login
        self.jwt_token = None

        # SmartConnect SDK instance (initialized during login)
        self.smart = None

    # ---------------------------------------------------------
    # LOGIN
    # ---------------------------------------------------------

    def login(self):
        """
        Perform SmartAPI login using TOTP authentication.

        Steps:
        ------
        1. Validate credentials
        2. Generate TOTP using secret
        3. Create SmartConnect instance
        4. Call generateSession()
        5. Store JWT token for future use

        Returns:
            dict : Raw login response from SmartAPI

        Raises:
            Exception if login fails
        """

        # Validate required credentials exist
        if not all([
            self.api_key,
            self.username,
            self.password,
            self.totp_secret
        ]):
            raise ValueError("SmartAPI credentials missing in .env")

        try:
            print("Logging into SmartAPI...")

            # Generate time-based OTP
            totp = pyotp.TOTP(self.totp_secret).now()

            # Initialize SDK connection
            self.smart = SmartConnect(api_key=self.api_key)

            # Create session
            session = self.smart.generateSession(
                self.username,
                self.password,
                totp
            )

            # If login unsuccessful
            if not session.get("status"):
                raise Exception(f"Login failed: {session}")

            # Store JWT token internally
            self.jwt_token = session["data"]["jwtToken"]

            return session

        except Exception as e:
            raise Exception(f"SmartAPI Login Error: {str(e)}")


    # ---------------------------------------------------------
    # FETCH CANDLES
    # ---------------------------------------------------------

    def fetch_recent_candles(self, symbol_token, interval="ONE_MINUTE", n=100):
        """
        Fetch last N historical candles.

        Parameters:
        -----------
        symbol_token : str
            SmartAPI symbol token (NOT trading symbol name)
        interval : str
            Candle timeframe (e.g., ONE_MINUTE)
        n : int
            Number of recent candles to return

        Returns:
        --------
        list
            Last N candles in SmartAPI format:
            [
                [timestamp, open, high, low, close, volume],
                ...
            ]

        Raises:
        -------
        Exception if:
            - login not called
            - API fails
            - empty data received
        """

        # Must login first
        if not self.smart:
            raise Exception("Login must be called before fetching candles")

        try:
            # Define time range (last 5 days buffer)
            to_date = datetime.now()
            from_date = to_date - timedelta(days=5)

            params = {
                "exchange": "NSE",
                "symboltoken": symbol_token,
                "interval": interval,
                "fromdate": from_date.strftime("%Y-%m-%d %H:%M"),
                "todate": to_date.strftime("%Y-%m-%d %H:%M"),
            }

            # Call SmartAPI endpoint
            response = self.smart.getCandleData(params)

            # API returned failure
            if not response.get("status"):
                raise Exception(f"Candle fetch failed: {response}")

            data = response.get("data")

            # No candles returned
            if not data:
                raise Exception("Empty candle data received")

            # Return last N candles
            return data[-n:]

        except Exception as e:
            raise Exception(f"Candle Fetch Error: {str(e)}")

