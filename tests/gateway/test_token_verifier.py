from typing import Any, Generator, override

import pytest
import base64

from joserfc import jwk

from language_model_gateway.gateway.auth.config.auth_config import AuthConfig
from language_model_gateway.gateway.auth.config.auth_config_reader import (
    AuthConfigReader,
)
from language_model_gateway.gateway.auth.exceptions.authorization_bearer_token_expired_exception import (
    AuthorizationBearerTokenExpiredException,
)
from language_model_gateway.gateway.auth.models.token import Token
from language_model_gateway.gateway.auth.token_reader import TokenReader
from joserfc import jwt
import time

from language_model_gateway.gateway.utilities.environment_variables import (
    EnvironmentVariables,
)

# Sample JWKS and token generation for testing
SECRET = base64.urlsafe_b64encode(b"secret").rstrip(b"=").decode("utf-8")
JWKS: dict[str, list[dict[str, str | list[str]]]] = {
    "keys": [{"kty": "oct", "kid": "testkey", "k": SECRET}]
}

KID = "testkey"
ALGORITHM = "HS256"

openid_configuration = "https://fake-issuer/.well-known/openid-configuration"
jwks_uri = "https://fake-jwks-uri"


@pytest.fixture
def mock_jwks(httpx_mock: Any) -> Generator[None, Any, None]:
    httpx_mock.add_response(url=jwks_uri, json=JWKS)
    yield


@pytest.fixture
def mock_well_known_config(httpx_mock: Any) -> Generator[None, Any, None]:
    httpx_mock.add_response(
        url=openid_configuration,
        json={
            "jwks_uri": jwks_uri,
            "issuer": "https://fake-issuer",
        },
    )
    yield


class MockAuthConfigReader(AuthConfigReader):
    @override
    def get_auth_configs_for_all_auth_providers(self) -> list[AuthConfig]:
        return [
            AuthConfig(
                audience="test-audience",
                client_id="test-client-id",
                client_secret="test-client-secret",
                well_known_uri=openid_configuration,
                issuer="https://fake-issuer",
                auth_provider="fake-auth-provider",
            )
        ]


class MockTokenReader(TokenReader):
    pass
    # @override
    # async def fetch_well_known_config_and_jwks_async(self) -> None:
    #     self.jwks = KeySet.import_key_set(JWKS)


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
    token_reader: TokenReader = MockTokenReader(
        auth_config_reader=MockAuthConfigReader(
            environment_variables=EnvironmentVariables()
        )
    )
    header: str = "Bearer sometoken"
    assert token_reader.extract_token(authorization_header=header) == "sometoken"
    assert token_reader.extract_token(authorization_header=None) is None
    assert token_reader.extract_token(authorization_header="") is None
    assert token_reader.extract_token(authorization_header="Basic sometoken") is None


async def test_verify_token_valid(mock_jwks: Any, mock_well_known_config: Any) -> None:
    token_reader: TokenReader = MockTokenReader(
        auth_config_reader=MockAuthConfigReader(
            environment_variables=EnvironmentVariables()
        ),
        algorithms=[ALGORITHM],
    )
    token: str = create_jwt_token()
    token_item: Token | None = await token_reader.verify_token_async(token=token)
    assert token_item is not None
    assert token_item.subject == "1234567890"
    assert token_item.name == "John Doe"


async def test_verify_token_expired(
    mock_jwks: Any, mock_well_known_config: Any
) -> None:
    token_reader: TokenReader = MockTokenReader(
        auth_config_reader=MockAuthConfigReader(
            environment_variables=EnvironmentVariables()
        ),
        algorithms=[ALGORITHM],
    )
    token: str = create_jwt_token(exp_offset=-60)
    with pytest.raises(
        AuthorizationBearerTokenExpiredException, match="This OAuth Token has expired"
    ):
        await token_reader.verify_token_async(token=token)
