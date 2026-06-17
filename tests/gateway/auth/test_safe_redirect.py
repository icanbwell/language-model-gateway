"""Tests for GatewayTokenStorageAuthManager._is_safe_redirect."""

import pytest
from unittest.mock import MagicMock

from language_model_gateway.gateway.auth.gateway_token_storage_auth_manager import (
    GatewayTokenStorageAuthManager,
)


def _make_request(host: str = "gateway.example.com") -> MagicMock:
    request = MagicMock()
    request.headers = {"host": host}
    return request


class TestIsSafeRedirect:
    @pytest.mark.parametrize(
        "url",
        [
            "/skills/publish",
            "/auth/callback",
            "/",
        ],
    )
    def test_relative_paths_allowed(self, url: str) -> None:
        request = _make_request()
        assert (
            GatewayTokenStorageAuthManager._is_safe_redirect(url=url, request=request)
            is True
        )

    @pytest.mark.parametrize(
        "url",
        [
            "skills/publish",
            "page",
        ],
    )
    def test_relative_without_slash_allowed(self, url: str) -> None:
        request = _make_request()
        assert (
            GatewayTokenStorageAuthManager._is_safe_redirect(url=url, request=request)
            is True
        )

    def test_same_host_absolute_url_allowed(self) -> None:
        request = _make_request("gateway.example.com")
        url = "https://gateway.example.com/skills/publish"
        assert (
            GatewayTokenStorageAuthManager._is_safe_redirect(url=url, request=request)
            is True
        )

    @pytest.mark.parametrize(
        "url",
        [
            "https://evil.com/steal-token",
            "https://attacker.example.com/callback",
            "http://other-host.com/",
        ],
    )
    def test_external_urls_rejected(self, url: str) -> None:
        request = _make_request("gateway.example.com")
        assert (
            GatewayTokenStorageAuthManager._is_safe_redirect(url=url, request=request)
            is False
        )

    def test_no_host_header_rejects_absolute_urls(self) -> None:
        request = _make_request("")
        url = "https://any-host.com/path"
        assert (
            GatewayTokenStorageAuthManager._is_safe_redirect(url=url, request=request)
            is False
        )
