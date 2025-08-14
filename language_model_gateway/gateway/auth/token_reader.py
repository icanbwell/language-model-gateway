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

from language_model_gateway.gateway.auth.config.auth_config import AuthConfig
from language_model_gateway.gateway.auth.config.auth_config_reader import (
    AuthConfigReader,
)
from language_model_gateway.gateway.auth.exceptions.authorization_bearer_token_expired_exception import (
    AuthorizationBearerTokenExpiredException,
)
from language_model_gateway.gateway.auth.exceptions.authorization_bearer_token_invalid_exception import (
    AuthorizationBearerTokenInvalidException,
)
from language_model_gateway.gateway.auth.exceptions.authorization_bearer_token_missing_exception import (
    AuthorizationBearerTokenMissingException,
)
from language_model_gateway.gateway.auth.models.token import Token

logger = logging.getLogger(__name__)


class TokenReader:
    """
    TokenReader is a utility class for reading and verifying JWT tokens using JWKS (JSON Web Key Set).
    """

    def __init__(
        self,
        *,
        algorithms: Optional[list[str]] = None,
        auth_config_reader: AuthConfigReader,
    ):
        """
        Initializes the TokenReader with the JWKS URI or Well-Known URI, issuer, audience, and algorithms.
        Args:
            algorithms (Optional[list[str]]): The list of algorithms to use for verifying the JWT.
            auth_config_reader (AuthConfigReader): The configuration reader for authentication settings.
        """
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

        self.auth_config_reader: AuthConfigReader = auth_config_reader
        assert self.auth_config_reader is not None, "AuthConfigReader must be provided"
        assert isinstance(self.auth_config_reader, AuthConfigReader)

        self.auth_configs: List[AuthConfig] = (
            self.auth_config_reader.get_auth_configs_for_all_audiences()
        )
        assert self.auth_configs, "At least one AuthConfig must be provided"

        self.well_known_configs: List[
            Dict[str, Any]
        ] = []  # will load asynchronously later
        self.jwks: KeySet = KeySet(keys=[])  # Will be set by async fetch

    @cached(ttl=60 * 60)
    async def fetch_well_known_config_and_jwks_async(self) -> None:
        """
        Fetches the JWKS from the provided URI or from the well-known OpenID Connect configuration.
        This method will fetch the JWKS and store it in the `self.jwks` attribute for later use.

        """

        self.well_known_configs = []  # Reset well-known configs before fetching
        self.jwks = KeySet(keys=[])  # Reset JWKS before fetching

        for auth_config in [c for c in self.auth_configs if c.well_known_uri]:
            if not auth_config.well_known_uri:
                logger.warning(
                    f"AuthConfig {auth_config} does not have a well-known URI, skipping JWKS fetch."
                )
                continue

            well_known_config: Dict[
                str, Any
            ] = await self.fetch_well_known_config_async(
                well_known_uri=auth_config.well_known_uri
            )

            jwks_uri = await self.get_jwks_uri_async(
                well_known_config=well_known_config
            )
            if not jwks_uri:
                logger.warning(
                    f"AuthConfig {auth_config} does not have a JWKS URI, skipping JWKS fetch."
                )
                continue

            async with httpx.AsyncClient() as client:
                try:
                    logger.info(f"Fetching JWKS from {jwks_uri}")
                    response = await client.get(jwks_uri)
                    response.raise_for_status()
                    jwks_data = response.json()
                    # Store all keys in a dict for fast lookup by kid
                    self.jwks.import_key_set(jwks_data)
                except httpx.HTTPStatusError as e:
                    raise ValueError(
                        f"Failed to fetch JWKS from {jwks_uri} with status {e.response.status_code} : {e}"
                    )
                except ConnectError as e:
                    raise ConnectionError(
                        f"Failed to connect to JWKS URI: {jwks_uri}: {e}"
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
            await self.fetch_well_known_config_and_jwks_async()
            assert self.jwks, "JWKS must be fetched before decoding tokens"
            try:
                decoded = jwt.decode(token, self.jwks, algorithms=self.algorithms)
                return decoded.claims
            except Exception as e:
                logger.error(f"Failed to decode token: {e}")
                raise AuthorizationBearerTokenMissingException(
                    message=f"Invalid token provided. Please check the token: {token}",
                ) from e
        else:
            try:
                token_content = jws.extract_compact(token.encode())
                return cast(Dict[str, Any], json.loads(token_content.payload))
            except Exception as e:
                logger.error(f"Failed to decode token without verification: {e}")
                raise AuthorizationBearerTokenInvalidException(
                    message=f"Invalid token provided. Please check the token: {token}",
                    token=token,
                ) from e

    async def verify_token_async(self, *, token: str) -> Token | None:
        """
        Verify a JWT token asynchronously using the JWKS from the provided URI.

        Args:
            token: The JWT token string to validate.
        Returns:
            The decoded claims if the token is valid.
        """
        assert token, "Token must not be empty"
        await self.fetch_well_known_config_and_jwks_async()
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
            # noinspection PyBroadException
            try:
                tz = ZoneInfo("America/New_York")
            except Exception:
                tz = None  # fallback to localtime if zoneinfo fails

            def to_eastern_time(ts: Optional[float]) -> str:
                """Convert a timestamp to a formatted string in Eastern Time (ET)."""
                if not ts:
                    return "None"
                # noinspection PyBroadException
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
            return Token.create(token=token)
        except ExpiredTokenError as e:
            logger.warning(f"Token has expired: {token}")
            raise AuthorizationBearerTokenExpiredException(
                message=f"This OAuth Token has expired. Exp: {exp_str}, Now: {now_str}.\nPlease Sign Out and Sign In to get a fresh OAuth token.",
                expires=exp_str,
                now=now_str,
                token=token,
            ) from e
        except Exception as e:
            raise AuthorizationBearerTokenInvalidException(
                message=f"Invalid token provided. Exp: {exp_str}, Now: {now_str}. Please check the token.",
                token=token,
            ) from e

    # noinspection PyMethodMayBeStatic
    async def fetch_well_known_config_async(
        self, *, well_known_uri: str
    ) -> Dict[str, Any]:
        """
        Fetches the OpenID Connect discovery document and returns its contents as a dict.
        Returns:
            dict: The parsed discovery document.
        Raises:
            ValueError: If the document cannot be fetched or parsed.
        """
        if not well_known_uri:
            raise ValueError("well_known_uri is not set")
        async with httpx.AsyncClient() as client:
            try:
                logger.info(f"Fetching OIDC discovery document from {well_known_uri}")
                response = await client.get(well_known_uri)
                response.raise_for_status()
                return cast(Dict[str, Any], response.json())
            except httpx.HTTPStatusError as e:
                raise ValueError(
                    f"Failed to fetch OIDC discovery document from {well_known_uri} with status {e.response.status_code} : {e}"
                )
            except ConnectError as e:
                raise ConnectionError(
                    f"Failed to connect to OIDC discovery document: {well_known_uri}: {e}"
                )

    # noinspection PyMethodMayBeStatic
    async def get_jwks_uri_async(
        self, *, well_known_config: Dict[str, Any]
    ) -> str | None:
        """
        Retrieves the JWKS URI and issuer from the well-known OpenID Connect configuration.
        Returns:
            tuple: (jwks_uri, issuer)
        Raises:
            ValueError: If required fields are missing.
        """
        jwks_uri: str | None = well_known_config.get("jwks_uri")
        issuer = well_known_config.get("issuer")
        if not jwks_uri or not issuer:
            raise ValueError("jwks_uri or issuer not found in well-known configuration")
        return jwks_uri

    async def get_subject_from_token_async(self, token: str) -> Optional[str]:
        """
        Extracts the 'sub' (subject) claim from the JWT token.
        Args:
            token (str): The JWT token string.
        Returns:
            Optional[str]: The subject claim if present, otherwise None.
        """
        assert token, "Token must not be empty"
        await self.fetch_well_known_config_and_jwks_async()
        assert self.jwks, "JWKS must be fetched before verifying tokens"
        try:
            claims = jwt.decode(token, self.jwks, algorithms=self.algorithms).claims
            return claims.get("email") or claims.get("sub")
        except Exception as e:
            logger.error(f"Failed to extract subject from token: {e}")
            return None

    async def get_expires_from_token_async(
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
        await self.fetch_well_known_config_and_jwks_async()
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
        await self.fetch_well_known_config_and_jwks_async()
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
        await self.fetch_well_known_config_and_jwks_async()
        assert self.jwks, "JWKS must be fetched before verifying tokens"
        try:
            claims = jwt.decode(token, self.jwks, algorithms=self.algorithms).claims
            return claims.get("aud")
        except Exception as e:
            logger.error(f"Failed to extract audience from token: {e}")
            return None

    async def get_issued_from_token_async(
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
        await self.fetch_well_known_config_and_jwks_async()
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
