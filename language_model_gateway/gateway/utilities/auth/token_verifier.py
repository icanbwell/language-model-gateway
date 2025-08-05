import json
from typing import Optional, Any, Dict, List

import httpx
from joserfc import jwt
from joserfc.jwk import KeySet, ECKey, OctKey, RSAKey, OKPKey


class TokenVerifier:
    def __init__(self, jwks_uri: str, algorithms: Optional[list[str]] = None):
        self.jwks_uri: str = jwks_uri
        self.algorithms: List[str] = algorithms or ["RS256"]
        self.jwks: KeySet | None = None  # Will be set by async fetch

    async def fetch_jwks_async(self) -> None:
        async with httpx.AsyncClient() as client:
            response = await client.get(self.jwks_uri)
            response.raise_for_status()
            jwks_data = response.json()
            # Store all keys in a dict for fast lookup by kid
            self.jwks = KeySet.import_key_set(jwks_data)

    def _get_key(self, kid: str) -> OctKey | RSAKey | ECKey | OKPKey:
        assert self.jwks, "JWKS must be fetched before getting keys"
        assert isinstance(self.jwks, KeySet)
        return self.jwks.get_by_kid(kid)

    @staticmethod
    def extract_token(authorization_header: str | None) -> Optional[str]:
        if not authorization_header:
            return None
        parts = authorization_header.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            return parts[1]
        return None

    async def verify_token_async(self, token: str) -> Dict[str, Any]:
        try:
            await self.fetch_jwks_async()
            # Extract header manually
            parts = token.split(".")
            if len(parts) != 3:
                raise ValueError("Invalid token format")

            # Decode header from base64url encoded first part
            import base64

            header_json = base64.urlsafe_b64decode(parts[0] + "==").decode("utf-8")
            header = json.loads(header_json)

            # Find the matching public key
            kid = header.get("kid")
            public_key: OctKey | RSAKey | ECKey | OKPKey = self._get_key(kid)

            # Validate the token
            verified = jwt.decode(token, public_key, algorithms=self.algorithms)

            # Create claims registry
            claims_requests = jwt.JWTClaimsRegistry()
            claims_requests.validate(verified.claims)

            return verified.claims

        except Exception as e:
            raise ValueError(f"Token validation failed: {str(e)}")
