import logging
import time
from typing import Optional, Any, Dict, List

import httpx
from httpx import ConnectError
from joserfc import jwt
from aiocache import cached
from joserfc.errors import ExpiredTokenError
from joserfc.jwk import KeySet

logger = logging.getLogger(__name__)


class TokenVerifier:
    def __init__(self, jwks_uri: Optional[str], algorithms: Optional[list[str]] = None):
        assert jwks_uri, "JWKS URI must be provided"
        assert isinstance(jwks_uri, str), "JWKS URI must be a string"
        self.jwks_uri: str = jwks_uri
        self.algorithms: List[str] = algorithms or ["RS256"]
        self.jwks: KeySet | None = None  # Will be set by async fetch

    @cached(ttl=60 * 60)
    async def fetch_jwks_async(self) -> None:
        async with httpx.AsyncClient() as client:
            try:
                logger.debug(f"Fetching JWKS from {self.jwks_uri}")
                response = await client.get(self.jwks_uri)
                response.raise_for_status()
                jwks_data = response.json()
                # Store all keys in a dict for fast lookup by kid
                self.jwks = KeySet.import_key_set(jwks_data)
            except httpx.HTTPStatusError as e:
                raise ValueError(
                    f"Failed to fetch JWKS from {self.jwks_uri} with status {e.response.status_code} : {e}"
                )
            except ConnectError as e:
                raise ConnectionError(
                    f"Failed to connect to JWKS URI: {self.jwks_uri}: {e}"
                )

    @staticmethod
    def extract_token(authorization_header: str | None) -> Optional[str]:
        if not authorization_header:
            return None
        parts = authorization_header.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            return parts[1]
        return None

    async def verify_token_async(self, *, token: str) -> Dict[str, Any]:
        """
        Verify a JWT token asynchronously using the JWKS from the provided URI.

        Args:
            token: The JWT token string to validate.
        Returns:
            The decoded claims if the token is valid.
        """
        assert token, "Token must not be empty"
        await self.fetch_jwks_async()
        assert self.jwks, "JWKS must be fetched before verifying tokens"

        exp_str: str = "None"
        now_str: str = "None"
        try:
            # Validate the token
            verified = jwt.decode(token, self.jwks, algorithms=self.algorithms)

            exp = verified.claims.get("exp")
            now = time.time()
            # convert exp to string for logging
            exp_str = (
                time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(exp))
                if exp
                else "None"
            )
            now_str = (
                time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now))
                if exp
                else "None"
            )
            # Create claims registry
            claims_requests = jwt.JWTClaimsRegistry()
            claims_requests.validate(verified.claims)

            logger.debug(f"Successfully verified token: {token}")

            return verified.claims
        except ExpiredTokenError as e:
            logger.warning(f"Token has expired: {token}")
            raise ValueError(
                f"This OAuth Token has expired. Exp: {exp_str}, Now: {now_str}. Please logout and login to get a fresh OAuth token."
            ) from e
        except Exception as e:
            raise ValueError(
                f"Invalid token provided. Exp: {exp_str}, Now: {now_str}. Please check the token."
            ) from e
