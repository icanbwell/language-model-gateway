from typing import override

from starlette.responses import Response

from languagemodelcommon.auth.token_storage_auth_manager import TokenStorageAuthManager
from language_model_gateway.gateway.utilities.auth_success_page import (
    build_auth_success_page,
)


class GatewayTokenStorageAuthManager(TokenStorageAuthManager):
    """Gateway-specific TokenStorageAuthManager that renders the HTML success page."""

    @override
    async def get_html_response(self, access_token: str | None) -> Response:
        return build_auth_success_page(access_token)
