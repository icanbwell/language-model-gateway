import secrets
from typing import Any

import httpx
from authlib.integrations.httpx_client import AsyncOAuth2Client
from authlib.oauth2.rfc6749 import OAuth2Token


class OIDCAuthPKCE:
    def __init__(
        self,
        *,
        well_known_url: str | None,
        client_id: str | None,
        redirect_uri: str | None,
    ):
        assert well_known_url, "Well-known URL must be provided"
        assert client_id, "Client ID must be provided"
        assert redirect_uri, "Redirect URI must be provided"
        self.well_known_url: str = well_known_url
        self.client_id: str = client_id
        self.redirect_uri: str = redirect_uri
        self._metadata = None

    async def fetch_metadata(self) -> None:
        async with httpx.AsyncClient() as client:
            resp = await client.get(self.well_known_url)
            resp.raise_for_status()
            self._metadata = resp.json()

    async def get_authorization_url(self, state: str) -> tuple[str, str]:
        if not self._metadata:
            await self.fetch_metadata()
        assert self._metadata, (
            "Metadata must be fetched before getting authorization URL"
        )
        code_verifier = secrets.token_urlsafe(64)
        authorization_endpoint = self._metadata["authorization_endpoint"]
        assert authorization_endpoint, "Authorization endpoint must be provided"
        token_endpoint = self._metadata["token_endpoint"]
        assert token_endpoint, "Token endpoint must be provided"
        oauth_client = AsyncOAuth2Client(
            client_id=self.client_id,
            redirect_uri=self.redirect_uri,
            scope="openid profile email",
            authorization_endpoint=authorization_endpoint,
            token_endpoint=token_endpoint,
        )
        uri, _ = oauth_client.create_authorization_url(
            authorization_endpoint,
            state=state,
            code_challenge_method="S256",
            code_verifier=code_verifier,
        )
        return uri, code_verifier

    async def exchange_code(self, code: str, code_verifier: str) -> dict[str, Any]:
        if not self._metadata:
            await self.fetch_metadata()
        assert self._metadata, "Metadata must be fetched before exchanging code"
        authorization_endpoint = self._metadata["authorization_endpoint"]
        assert authorization_endpoint, "Authorization endpoint must be provided"
        token_endpoint = self._metadata["token_endpoint"]
        assert token_endpoint, "Token endpoint must be provided"
        oauth_client = AsyncOAuth2Client(
            client_id=self.client_id,
            redirect_uri=self.redirect_uri,
            scope="openid profile email",
            authorization_endpoint=authorization_endpoint,
            token_endpoint=token_endpoint,
        )
        token: dict[str, str] | OAuth2Token = await oauth_client.fetch_token(
            token_endpoint,
            code=code,
            code_verifier=code_verifier,
            client_id=self.client_id,
            redirect_uri=self.redirect_uri,
        )
        return token
