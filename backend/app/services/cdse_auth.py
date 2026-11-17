import time
import logging
import requests
from typing import Optional, Dict, Any
from app.core.config import settings

logger = logging.getLogger(__name__)


class CDSEAuthenticationError(Exception):
    """Base exception for CDSE OAuth authentication failures."""
    pass


class CDSEAuthService:
    def __init__(self):
        self._cached_token: Optional[str] = None
        self._token_expiry: float = 0.0

    def get_access_token(self, force_refresh: bool = False) -> str:
        """
        Retrieves a valid OAuth2 Access Token for CDSE Sentinel Hub.
        Reuses cached token while valid to avoid excessive token requests.
        """
        now = time.time()
        if not force_refresh and self._cached_token and now < (self._token_expiry - 30):
            return self._cached_token

        client_id = settings.CDSE_CLIENT_ID
        client_secret = settings.CDSE_CLIENT_SECRET
        token_url = settings.CDSE_TOKEN_URL

        if not client_id or not client_secret or client_id.startswith("your_") or client_secret.startswith("your_"):
            raise CDSEAuthenticationError(
                "CDSE credentials are not configured. Please set CDSE_CLIENT_ID and CDSE_CLIENT_SECRET in backend/.env"
            )

        payload = {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
        }

        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }

        last_err: Optional[Exception] = None
        for attempt in range(1, 4):
            try:
                response = requests.post(
                    token_url,
                    data=payload,
                    headers=headers,
                    timeout=20.0
                )
                break
            except requests.exceptions.RequestException as e:
                last_err = e
                logger.warning("CDSE Auth attempt %d/3 failed: %s. Retrying...", attempt, str(e))
                time.sleep(1.0)
        else:
            raise CDSEAuthenticationError(f"Network error connecting to CDSE auth endpoint after 3 attempts: {str(last_err)}")

        if response.status_code == 401:
            raise CDSEAuthenticationError(
                "Authentication failed (401 Unauthorized): Invalid CDSE Client ID or Client Secret."
            )
        elif response.status_code == 403:
            raise CDSEAuthenticationError(
                "Authentication forbidden (403 Forbidden): Account permissions issue or scope restriction."
            )
        elif response.status_code == 429:
            raise CDSEAuthenticationError(
                "Rate limit exceeded (429 Too Many Requests): Please retry after a brief pause."
            )
        elif response.status_code >= 500:
            raise CDSEAuthenticationError(
                f"CDSE Auth service error ({response.status_code}): Service temporarily unavailable."
            )
        elif response.status_code != 200:
            raise CDSEAuthenticationError(
                f"Unexpected token response status {response.status_code}: {response.text[:200]}"
            )

        try:
            data: Dict[str, Any] = response.json()
            access_token = data.get("access_token")
            expires_in = data.get("expires_in", 3600)

            if not access_token:
                raise CDSEAuthenticationError("Response JSON did not contain 'access_token'.")

            self._cached_token = access_token
            self._token_expiry = now + float(expires_in)
            logger.info("Successfully acquired CDSE access token (expires in %ds)", expires_in)
            return access_token

        except ValueError:
            raise CDSEAuthenticationError("Invalid JSON returned from CDSE token endpoint.")


# Global singleton instance
cdse_auth = CDSEAuthService()


def get_access_token(force_refresh: bool = False) -> str:
    """Convenience helper function to retrieve CDSE OAuth access token."""
    return cdse_auth.get_access_token(force_refresh=force_refresh)
