from typing import Any, Generator

import pytest
import base64

from joserfc import jwk

from language_model_gateway.gateway.auth.models.token_item import TokenItem
from language_model_gateway.gateway.auth.token_reader import TokenReader
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
    token_reader: TokenReader = TokenReader(jwks_uri="https://fake-jwks-uri")
    header: str = "Bearer sometoken"
    assert token_reader.extract_token(header) == "sometoken"
    assert token_reader.extract_token(None) is None
    assert token_reader.extract_token("") is None
    assert token_reader.extract_token("Basic sometoken") is None


async def test_verify_token_valid(mock_jwks: Any) -> None:
    token_reader: TokenReader = TokenReader(
        jwks_uri="https://fake-jwks-uri", algorithms=[ALGORITHM]
    )
    token: str = create_jwt_token()
    token_item: TokenItem | None = await token_reader.verify_token_async(token=token)
    assert token_item is not None
    assert token_item.subject == "1234567890"
    assert token_item.id_token_claims
    assert token_item.id_token_claims["name"] == "John Doe"


async def test_verify_token_expired(mock_jwks: Any) -> None:
    token_reader: TokenReader = TokenReader(
        jwks_uri="https://fake-jwks-uri", algorithms=[ALGORITHM]
    )
    token: str = create_jwt_token(exp_offset=-60)
    with pytest.raises(ValueError, match="This OAuth Token has expired"):
        await token_reader.verify_token_async(token=token)
