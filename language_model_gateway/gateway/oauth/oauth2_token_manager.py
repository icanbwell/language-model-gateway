import asyncio
import logging
import time
from typing import Optional, Dict, List
import aiohttp
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class OAuth2Token:
    """OAuth2 token data"""

    access_token: str
    token_type: str = "Bearer"
    expires_in: Optional[int] = None
    refresh_token: Optional[str] = None
    scope: Optional[str] = None
    expires_at: Optional[float] = None

    def __post_init__(self):
        """Calculate expiration time if expires_in is provided"""
        if self.expires_in and not self.expires_at:
            self.expires_at = time.time() + self.expires_in

    @property
    def is_expired(self) -> bool:
        """Check if the token is expired"""
        if not self.expires_at:
            return False
        return time.time() >= (self.expires_at - 60)  # 60 second buffer

    @property
    def authorization_header(self) -> str:
        """Get the authorization header value"""
        return f"{self.token_type} {self.access_token}"


class OAuth2TokenManager:
    """Manages OAuth2 tokens for MCP servers"""

    def __init__(self):
        self._tokens: Dict[str, OAuth2Token] = {}
        self._lock = asyncio.Lock()

    async def get_token(
        self,
        server_name: str,
        token_url: str,
        client_id: str,
        client_secret: str,
        scopes: Optional[List[str]] = None,
        force_refresh: bool = False,
    ) -> OAuth2Token:
        """
        Get a valid OAuth2 token for the given server.

        Args:
            server_name: Unique identifier for the server
            token_url: OAuth2 token endpoint URL
            client_id: OAuth2 client ID
            client_secret: OAuth2 client secret
            scopes: List of OAuth2 scopes
            force_refresh: Force refresh even if token is valid

        Returns:
            OAuth2Token object
        """
        async with self._lock:
            # Check if we have a valid token
            if (
                not force_refresh
                and server_name in self._tokens
                and not self._tokens[server_name].is_expired
            ):
                return self._tokens[server_name]

            # Request new token
            token = await self._request_token(
                token_url, client_id, client_secret, scopes
            )
            self._tokens[server_name] = token
            return token

    async def _request_token(
        self,
        token_url: str,
        client_id: str,
        client_secret: str,
        scopes: Optional[List[str]] = None,
    ) -> OAuth2Token:
        """
        Request a new OAuth2 token from the authorization server.

        Args:
            token_url: OAuth2 token endpoint URL
            client_id: OAuth2 client ID
            client_secret: OAuth2 client secret
            scopes: List of OAuth2 scopes

        Returns:
            OAuth2Token object

        Raises:
            Exception: If token request fails
        """
        data = {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
        }

        if scopes:
            data["scope"] = " ".join(scopes)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    token_url,
                    data=data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(
                            f"OAuth2 token request failed: {response.status} - {error_text}"
                        )

                    token_data = await response.json()
                    return OAuth2Token(
                        access_token=token_data["access_token"],
                        token_type=token_data.get("token_type", "Bearer"),
                        expires_in=token_data.get("expires_in"),
                        refresh_token=token_data.get("refresh_token"),
                        scope=token_data.get("scope"),
                    )
        except Exception as e:
            logger.error(f"Failed to request OAuth2 token: {e}")
            raise

    def clear_token(self, server_name: str) -> None:
        """Clear the cached token for a server"""
        if server_name in self._tokens:
            del self._tokens[server_name]

    def clear_all_tokens(self) -> None:
        """Clear all cached tokens"""
        self._tokens.clear()
