import datetime
import logging
import time
from typing import Optional, Any, Dict, List, cast

import httpx
from httpx import ConnectError
from joserfc import jwt
from aiocache import cached
from joserfc.errors import ExpiredTokenError
from joserfc.jwk import KeySet

from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)


class TokenVerifier:
    def __init__(
        self,
        *,
        jwks_uri: Optional[str] = None,
        well_known_uri: Optional[str] = None,
        issuer: Optional[str] = None,
        audience: Optional[str] = None,
        algorithms: Optional[list[str]] = None,
    ):
        assert jwks_uri or well_known_uri, (
            "Either JWKS URI or Well-Known URI must be provided"
        )
        self.jwks_uri: Optional[str] = jwks_uri
        self.well_known_uri: Optional[str] = well_known_uri
        self.algorithms: List[str] = algorithms or ["RS256"]
        self.jwks: KeySet | None = None  # Will be set by async fetch
        self.issuer: Optional[str] = issuer
        self.audience: Optional[str] = audience

    @cached(ttl=60 * 60)
    async def fetch_jwks_async(self) -> None:
        # if we don't have a JWKS URI, try to fetch it from the well-known configuration
        if not self.jwks_uri:
            if not self.well_known_uri:
                raise ValueError("Neither JWKS URI nor Well-Known URI is set")
            self.jwks_uri, self.issuer = await self.get_jwks_uri_and_issuer_async()

        async with httpx.AsyncClient() as client:
            try:
                logger.info(f"Fetching JWKS from {self.jwks_uri}")
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
            # convert exp and now to ET (America/New_York) for logging
            tz = None
            try:
                tz = ZoneInfo("America/New_York")
            except Exception:
                tz = None  # fallback to localtime if zoneinfo fails

            def to_eastern_time(ts: Optional[float]) -> str:
                """Convert a timestamp to a formatted string in Eastern Time (ET)."""
                if not ts:
                    return "None"
                try:
                    dt = (
                        datetime.datetime.fromtimestamp(ts, tz)
                        if tz
                        else datetime.datetime.fromtimestamp(ts)
                    )
                    return dt.strftime("%Y-%m-%d %I:%M:%S %p %Z")  # AM/PM format
                except Exception:
                    return str(ts)

            exp_str = to_eastern_time(exp)
            now_str = to_eastern_time(now)
            # Create claims registry
            claims_requests = jwt.JWTClaimsRegistry()
            claims_requests.validate(verified.claims)

            logger.debug(f"Successfully verified token: {token}")

            return verified.claims
        except ExpiredTokenError as e:
            logger.warning(f"Token has expired: {token}")
            raise ValueError(
                f"This OAuth Token has expired. Exp: {exp_str}, Now: {now_str}.\nPlease Sign Out and Sign In to get a fresh OAuth token."
            ) from e
        except Exception as e:
            raise ValueError(
                f"Invalid token provided. Exp: {exp_str}, Now: {now_str}. Please check the token."
            ) from e

    async def fetch_well_known_config_async(self) -> Dict[str, Any]:
        """
        Fetches the OpenID Connect discovery document and returns its contents as a dict.
        Returns:
            dict: The parsed discovery document.
        Raises:
            ValueError: If the document cannot be fetched or parsed.
        """
        if not self.well_known_uri:
            raise ValueError("well_known_uri is not set")
        async with httpx.AsyncClient() as client:
            try:
                logger.info(
                    f"Fetching OIDC discovery document from {self.well_known_uri}"
                )
                response = await client.get(self.well_known_uri)
                response.raise_for_status()
                return cast(Dict[str, Any], response.json())
            except httpx.HTTPStatusError as e:
                raise ValueError(
                    f"Failed to fetch OIDC discovery document from {self.well_known_uri} with status {e.response.status_code} : {e}"
                )
            except ConnectError as e:
                raise ConnectionError(
                    f"Failed to connect to OIDC discovery document: {self.well_known_uri}: {e}"
                )

    async def get_jwks_uri_and_issuer_async(self) -> tuple[str, str]:
        """
        Retrieves the JWKS URI and issuer from the well-known OpenID Connect configuration.
        Returns:
            tuple: (jwks_uri, issuer)
        Raises:
            ValueError: If required fields are missing.
        """
        config = await self.fetch_well_known_config_async()
        jwks_uri = config.get("jwks_uri")
        issuer = config.get("issuer")
        if not jwks_uri or not issuer:
            raise ValueError("jwks_uri or issuer not found in well-known configuration")
        return jwks_uri, issuer
