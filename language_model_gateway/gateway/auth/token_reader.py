import datetime
import json
import logging
import time
from typing import Optional, Any, Dict, List, cast

import httpx
from httpx import ConnectError
from joserfc import jwt, jws
from aiocache import cached
from joserfc.errors import ExpiredTokenError
from joserfc.jwk import KeySet

from zoneinfo import ZoneInfo

from language_model_gateway.gateway.auth.exceptions.authorization_needed_exception import (
    AuthorizationNeededException,
)

logger = logging.getLogger(__name__)


class TokenReader:
    """
    TokenReader is a utility class for reading and verifying JWT tokens using JWKS (JSON Web Key Set).
    """

    def __init__(
        self,
        *,
        jwks_uri: Optional[str] = None,
        well_known_uri: Optional[str] = None,
        issuer: Optional[str] = None,
        audience: Optional[str] = None,
        algorithms: Optional[list[str]] = None,
    ):
        """
        Initializes the TokenReader with the JWKS URI or Well-Known URI, issuer, audience, and algorithms.
        Args:
            jwks_uri (Optional[str]): The URI to fetch the JWKS from.
            well_known_uri (Optional[str]): The URI to fetch the OpenID Connect discovery document.
            issuer (Optional[str]): The expected issuer of the JWT.
            audience (Optional[str]): The expected audience of the JWT.
            algorithms (Optional[list[str]]): The list of algorithms to use for verifying the JWT.
        """
        assert jwks_uri or well_known_uri, (
            "Either JWKS URI or Well-Known URI must be provided"
        )
        self.jwks_uri: Optional[str] = jwks_uri
        self.well_known_uri: Optional[str] = well_known_uri
        self.algorithms: List[str] = algorithms or [
            "RS256",
            "RS384",
            "RS512",
            "HS256",
            "HS384",
            "HS512",
            "ES256",
            "ES384",
            "ES512",
            "PS256",
            "PS384",
            "PS512",
        ]
        self.jwks: KeySet | None = None  # Will be set by async fetch
        self.issuer: Optional[str] = issuer
        self.audience: Optional[str] = audience

    @cached(ttl=60 * 60)
    async def fetch_jwks_async(self) -> None:
        """
        Fetches the JWKS from the provided URI or from the well-known OpenID Connect configuration.
        This method will fetch the JWKS and store it in the `self.jwks` attribute for later use.

        """
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
        """
        Extracts the JWT token from the Authorization header.
        Args:
            authorization_header (str | None): The Authorization header string.
        Returns:
            Optional[str]: The extracted JWT token if present, otherwise None.
        """
        if not authorization_header:
            return None
        parts = authorization_header.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            return parts[1]
        return None

    async def decode_token_async(
        self, *, token: str, verify_signature: bool
    ) -> Dict[str, Any] | None:
        """
        Decode a JWT token, optionally without verifying its signature.
        Args:
            token (str): The JWT token string to decode.
            verify_signature (bool): Whether to verify the signature using JWKS. Default is True.
        Returns:
            Dict[str, Any]: The decoded claims of the JWT token, or None if not a JWT.
        """
        assert token, "Token must not be empty"
        # Only attempt to decode if token looks like a JWT (contains two dots)
        if token.count(".") != 2:
            logger.warning(
                f"Token does not appear to be a JWT, skipping decode: {token}"
            )
            return None
        if verify_signature:
            await self.fetch_jwks_async()
            assert self.jwks, "JWKS must be fetched before decoding tokens"
            try:
                decoded = jwt.decode(token, self.jwks, algorithms=self.algorithms)
                return decoded.claims
            except Exception as e:
                logger.error(f"Failed to decode token: {e}")
                raise AuthorizationNeededException(
                    f"Invalid token provided. Please check the token: {token}"
                ) from e
        else:
            try:
                token_content = jws.extract_compact(token.encode())
                return cast(Dict[str, Any], json.loads(token_content.payload))
            except Exception as e:
                logger.error(f"Failed to decode token without verification: {e}")
                raise AuthorizationNeededException(
                    f"Invalid token provided. Please check the token: {token}"
                ) from e

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
            raise AuthorizationNeededException(
                f"This OAuth Token has expired. Exp: {exp_str}, Now: {now_str}.\nPlease Sign Out and Sign In to get a fresh OAuth token."
            ) from e
        except Exception as e:
            raise AuthorizationNeededException(
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

    async def get_subject_from_token_async(self, token: str) -> Optional[str]:
        """
        Extracts the 'sub' (subject) claim from the JWT token.
        Args:
            token (str): The JWT token string.
        Returns:
            Optional[str]: The subject claim if present, otherwise None.
        """
        assert token, "Token must not be empty"
        await self.fetch_jwks_async()
        assert self.jwks, "JWKS must be fetched before verifying tokens"
        try:
            claims = jwt.decode(token, self.jwks, algorithms=self.algorithms).claims
            return claims.get("email") or claims.get("sub")
        except Exception as e:
            logger.error(f"Failed to extract subject from token: {e}")
            return None

    async def get_expiration_from_token_async(
        self, token: str
    ) -> Optional[datetime.datetime]:
        """
        Extracts the 'exp' (expiration) claim from the JWT token.
        Args:
            token (str): The JWT token string.
        Returns:
            Optional[datetime.datetime]: The expiration time as a datetime object if present, otherwise None.
        """
        assert token, "Token must not be empty"
        await self.fetch_jwks_async()
        assert self.jwks, "JWKS must be fetched before verifying tokens"
        try:
            claims = jwt.decode(token, self.jwks, algorithms=self.algorithms).claims
            exp = claims.get("exp")
            if exp:
                return datetime.datetime.fromtimestamp(exp, tz=ZoneInfo("UTC"))
            return None
        except Exception as e:
            logger.error(f"Failed to extract expiration from token: {e}")
            return None

    async def get_issuer_from_token_async(self, token: str) -> Optional[str]:
        """
        Extracts the 'iss' (issuer) claim from the JWT token.
        Args:
            token (str): The JWT token string.
        Returns:
            Optional[str]: The issuer claim if present, otherwise None.
        """
        assert token, "Token must not be empty"
        await self.fetch_jwks_async()
        assert self.jwks, "JWKS must be fetched before verifying tokens"
        try:
            claims = jwt.decode(token, self.jwks, algorithms=self.algorithms).claims
            return claims.get("iss")
        except Exception as e:
            logger.error(f"Failed to extract issuer from token: {e}")
            return None

    async def get_audience_from_token_async(self, token: str) -> Optional[str]:
        """
        Extracts the 'aud' (audience) claim from the JWT token.
        Args:
            token (str): The JWT token string.
        Returns:
            Optional[str]: The audience claim if present, otherwise None.
        """
        assert token, "Token must not be empty"
        await self.fetch_jwks_async()
        assert self.jwks, "JWKS must be fetched before verifying tokens"
        try:
            claims = jwt.decode(token, self.jwks, algorithms=self.algorithms).claims
            return claims.get("aud")
        except Exception as e:
            logger.error(f"Failed to extract audience from token: {e}")
            return None

    async def get_created_at_from_token_async(
        self, token: str
    ) -> Optional[datetime.datetime]:
        """
        Extracts the 'iat' (issued at) claim from the JWT token.
        Args:
            token (str): The JWT token string.
        Returns:
            Optional[datetime.datetime]: The issued at time as a datetime object if present, otherwise None.
        """
        assert token, "Token must not be empty"
        await self.fetch_jwks_async()
        assert self.jwks, "JWKS must be fetched before verifying tokens"
        try:
            claims = jwt.decode(token, self.jwks, algorithms=self.algorithms).claims
            iat = claims.get("iat")
            if iat:
                return datetime.datetime.fromtimestamp(iat, tz=ZoneInfo("UTC"))
            return None
        except Exception as e:
            logger.error(f"Failed to extract created at from token: {e}")
            return None
