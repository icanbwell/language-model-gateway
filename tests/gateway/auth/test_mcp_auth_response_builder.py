"""Tests for McpAuthResponseBuilder."""

import pytest
from httpx import Headers
from unittest.mock import patch

from language_model_gateway.gateway.auth.mcp_auth_response_builder import (
    McpAuthResponseBuilder,
)
from languagemodelcommon.mcp.exceptions.mcp_tool_unauthorized_exception import (
    McpToolUnauthorizedException,
)
from oidcauthlib.auth.exceptions.authorization_needed_exception import (
    AuthorizationNeededException,
)


@pytest.fixture
def builder() -> McpAuthResponseBuilder:
    return McpAuthResponseBuilder()


class TestFromAuthorizationNeeded:
    def test_splits_multiline_message(self, builder: McpAuthResponseBuilder) -> None:
        exception = AuthorizationNeededException(
            message="Line one\nLine two\nLine three"
        )
        result = builder.from_authorization_needed(exception)
        assert result == ["Line one", "Line two", "Line three"]

    def test_strips_whitespace(self, builder: McpAuthResponseBuilder) -> None:
        exception = AuthorizationNeededException(message="  padded  \n  text  ")
        result = builder.from_authorization_needed(exception)
        assert result == ["padded", "text"]

    def test_filters_blank_lines(self, builder: McpAuthResponseBuilder) -> None:
        exception = AuthorizationNeededException(message="first\n\n\nsecond\n  \nthird")
        result = builder.from_authorization_needed(exception)
        assert result == ["first", "second", "third"]

    def test_single_line(self, builder: McpAuthResponseBuilder) -> None:
        exception = AuthorizationNeededException(message="Please authenticate")
        result = builder.from_authorization_needed(exception)
        assert result == ["Please authenticate"]

    def test_empty_message(self, builder: McpAuthResponseBuilder) -> None:
        exception = AuthorizationNeededException(message="")
        result = builder.from_authorization_needed(exception)
        assert result == []


class TestFromMcpToolUnauthorized:
    def test_builds_message_from_headers(self, builder: McpAuthResponseBuilder) -> None:
        exception = McpToolUnauthorizedException(
            message="Unauthorized",
            url="https://mcp.example.com/tool",
            status_code=401,
            headers=Headers({
                "WWW-Authenticate": 'Bearer resource_metadata="https://mcp.example.com/.well-known/oauth-protected-resource"'
            }),
        )
        with patch(
            "language_model_gateway.gateway.auth.mcp_auth_response_builder.McpAuthorizationHelper"
        ) as mock_helper:
            mock_helper.extract_resource_metadata_from_www_auth.return_value = (
                "https://mcp.example.com/.well-known/oauth-protected-resource"
            )
            mock_helper.build_www_authenticate_login_message.return_value = (
                "Please login at https://mcp.example.com"
            )
            result = builder.from_mcp_tool_unauthorized(exception)

        assert result == ["Please login at https://mcp.example.com"]
        mock_helper.build_www_authenticate_login_message.assert_called_once_with(
            resource_metadata_url="https://mcp.example.com/.well-known/oauth-protected-resource",
            tool_url="https://mcp.example.com/tool",
        )

    def test_no_headers(self, builder: McpAuthResponseBuilder) -> None:
        exception = McpToolUnauthorizedException(
            message="Unauthorized",
            url="https://mcp.example.com/tool",
            status_code=401,
            headers=None,
        )
        with patch(
            "language_model_gateway.gateway.auth.mcp_auth_response_builder.McpAuthorizationHelper"
        ) as mock_helper:
            mock_helper.build_www_authenticate_login_message.return_value = (
                "Auth required for https://mcp.example.com/tool"
            )
            result = builder.from_mcp_tool_unauthorized(exception)

        assert result == ["Auth required for https://mcp.example.com/tool"]
        mock_helper.extract_resource_metadata_from_www_auth.assert_not_called()
        mock_helper.build_www_authenticate_login_message.assert_called_once_with(
            resource_metadata_url=None,
            tool_url="https://mcp.example.com/tool",
        )

    def test_returns_single_element_list(self, builder: McpAuthResponseBuilder) -> None:
        exception = McpToolUnauthorizedException(
            message="Unauthorized",
            url="https://mcp.example.com/tool",
            status_code=401,
            headers=Headers({}),
        )
        with patch(
            "language_model_gateway.gateway.auth.mcp_auth_response_builder.McpAuthorizationHelper"
        ) as mock_helper:
            mock_helper.extract_resource_metadata_from_www_auth.return_value = None
            mock_helper.build_www_authenticate_login_message.return_value = "msg"
            result = builder.from_mcp_tool_unauthorized(exception)

        assert len(result) == 1
