# trading/services/session_manager.py

from django.core.cache import cache
from trading.services.angelone_service import AngelOneService


class SmartAPISessionManager:
    """
    Handles SmartAPI login session caching and reuse.
    """

    CACHE_KEY = "smartapi_session"

    def __init__(self):
        self.service = AngelOneService()

    def get_valid_session(self):
        """
        Returns valid SmartAPI session.
        Logs in only if not cached.
        """

        session = cache.get(self.CACHE_KEY)

        if session:
            return session  # Reuse cached session

        # No cached session → login
        login_response = self.service.login()

        if not login_response.get("status"):
            raise Exception("SmartAPI login failed")

        session_data = login_response["data"]

        # Store in cache (JWT expires ~1 hour, so 50 min safe)
        cache.set(self.CACHE_KEY, session_data, timeout=3000)

        return session_data

    def clear_session(self):
        """
        Force clear cached session (useful for debugging).
        """
        cache.delete(self.CACHE_KEY)
