from typing import Any, Generator

import pytest
import base64

from joserfc import jwk

from language_model_gateway.gateway.utilities.auth.token_verifier import TokenVerifier
from joserfc import jwt
import time

# Sample JWKS and token generation for testing
SECRET = base64.urlsafe_b64encode(b"secret").rstrip(b"=").decode("utf-8")
JWKS: dict[str, list[dict[str, str | list[str]]]] = {
    "keys": [{"kty": "oct", "kid": "testkey", "k": SECRET}]
}

KID = "testkey"
ALGORITHM = "HS256"


@pytest.fixture
def mock_jwks(httpx_mock: Any) -> Generator[None, Any, None]:
    httpx_mock.add_response(json=JWKS)
    yield


def create_jwt_token(exp_offset: int = 60) -> str:
    header = {"kid": KID, "alg": ALGORITHM}
    payload = {
        "sub": "1234567890",
        "name": "John Doe",
        "exp": int(time.time()) + exp_offset,
    }
    # joserfc requires key as dict for oct (symmetric) keys
    key = jwk.import_key(JWKS["keys"][0])
    return jwt.encode(header=header, claims=payload, key=key)


def test_extract_token() -> None:
    verifier = TokenVerifier(jwks_uri="https://fake-jwks-uri")
    header = "Bearer sometoken"
    assert verifier.extract_token(header) == "sometoken"
    assert verifier.extract_token(None) is None
    assert verifier.extract_token("") is None
    assert verifier.extract_token("Basic sometoken") is None


async def test_verify_token_valid(mock_jwks: Any) -> None:
    verifier = TokenVerifier(jwks_uri="https://fake-jwks-uri", algorithms=[ALGORITHM])
    token = create_jwt_token()
    claims = await verifier.verify_token_async(token=token)
    assert claims["sub"] == "1234567890"
    assert claims["name"] == "John Doe"


async def test_verify_token_expired(mock_jwks: Any) -> None:
    verifier = TokenVerifier(jwks_uri="https://fake-jwks-uri", algorithms=[ALGORITHM])
    token = create_jwt_token(exp_offset=-60)
    with pytest.raises(ValueError, match="This OAuth Token has expired"):
        await verifier.verify_token_async(token=token)
