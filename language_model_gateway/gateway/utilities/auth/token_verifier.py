from typing import Optional, Any, Dict, List

import httpx
from joserfc import jwt
from aiocache import cached
from joserfc.jwk import KeySet


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
            response = await client.get(self.jwks_uri)
            response.raise_for_status()
            jwks_data = response.json()
            # Store all keys in a dict for fast lookup by kid
            self.jwks = KeySet.import_key_set(jwks_data)

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

        # Validate the token
        verified = jwt.decode(token, self.jwks, algorithms=self.algorithms)

        # Create claims registry
        claims_requests = jwt.JWTClaimsRegistry()
        claims_requests.validate(verified.claims)

        return verified.claims
