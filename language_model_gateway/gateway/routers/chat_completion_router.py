import logging
import traceback
from datetime import datetime
from enum import Enum
from typing import Annotated, Dict, Any, TypedDict, Sequence

from botocore.exceptions import TokenRetrievalError
from fastapi import APIRouter, Depends, HTTPException
from fastapi import params
from oidcauthlib.auth.exceptions.authorization_needed_exception import (
    AuthorizationNeededException,
)
from starlette.requests import Request
from starlette.responses import StreamingResponse, JSONResponse

from oidcauthlib.auth.auth_manager import AuthManager
from oidcauthlib.auth.models.auth import AuthInformation
from oidcauthlib.auth.models.token import Token
from oidcauthlib.auth.token_reader import TokenReader
from language_model_gateway.gateway.managers.chat_completion_manager import (
    ChatCompletionManager,
)
from language_model_gateway.gateway.schema.openai.completions import ChatRequest
from language_model_gateway.gateway.schema.openai.responses import ResponsesRequest
from language_model_gateway.gateway.structures.openai.request.chat_completion_api_request_wrapper import (
    ChatCompletionApiRequestWrapper,
)
from language_model_gateway.gateway.structures.openai.request.chat_request_wrapper import (
    ChatRequestWrapper,
)
from language_model_gateway.gateway.structures.openai.request.responses_api_request_wrapper import (
    ResponsesApiRequestWrapper,
)
from language_model_gateway.gateway.utilities.language_model_gateway_environment_variables import (
    LanguageModelGatewayEnvironmentVariables,
)
from oidcauthlib.container.inject import Inject
from language_model_gateway.gateway.utilities.logger.log_levels import SRC_LOG_LEVELS

logger = logging.getLogger(__name__)
logger.setLevel(SRC_LOG_LEVELS["LLM"])


class ErrorDetail(TypedDict):
    message: str
    timestamp: str
    trace_id: str
    call_stack: str


class ChatCompletionsRouter:
    """
    Router class for chat completions endpoints
    """

    def __init__(
        self,
        *,
        prefix: str = "/api/v1",
        tags: list[str | Enum] | None = None,
        dependencies: Sequence[params.Depends] | None = None,
    ) -> None:
        self.prefix = prefix
        self.tags = tags or ["models"]
        self.dependencies = dependencies or []
        self.router = APIRouter(
            prefix=self.prefix, tags=self.tags, dependencies=self.dependencies
        )
        self._register_routes()

    def _register_routes(self) -> None:
        """Register all routes for this router"""
        self.router.add_api_route(
            "/chat/completions",
            self.chat_completions,
            methods=["POST"],
            response_model=None,
            summary="Complete a chat prompt",
            description="Completes a chat prompt using the specified model",
            response_description="Chat completions",
            status_code=200,
        )
        self.router.add_api_route(
            "/chat/completion",
            self.chat_completions,
            methods=["POST"],
            response_model=None,
            summary="Complete a chat prompt",
            description="Completes a chat prompt using the specified model",
            response_description="Chat completions",
            status_code=200,
        )
        self.router.add_api_route(
            "/responses",
            self.chat_responses,
            methods=["POST"],
            response_model=None,
            summary="Get responses for a chat prompt (OpenAI Responses API)",
            description="Returns responses for a chat prompt using the new OpenAI Responses API specification.",
            response_description="Chat responses",
            status_code=200,
        )

    # noinspection PyMethodMayBeStatic
    async def chat_completions(
        self,
        request: Request,
        chat_request: Dict[str, Any],
        chat_manager: Annotated[
            ChatCompletionManager, Depends(Inject(ChatCompletionManager))
        ],
        token_reader: Annotated[TokenReader, Depends(Inject(TokenReader))],
        auth_manager: Annotated[AuthManager, Depends(Inject(AuthManager))],
        environment_variables: Annotated[
            LanguageModelGatewayEnvironmentVariables,
            Depends(Inject(LanguageModelGatewayEnvironmentVariables)),
        ],
    ) -> StreamingResponse | JSONResponse:
        """
        Chat completions endpoint. chat_manager is injected by FastAPI.

        Args:
            request: The incoming request
            chat_request: The chat request data
            chat_manager: Injected chat manager instance
            token_reader: Injected token reader instance
            auth_manager: Injected auth manager instance
            environment_variables: Injected environment variables instance

        Returns:
            StreamingResponse or JSONResponse

        Raises:
            HTTPException: For various error conditions
        """
        if not chat_request:
            raise ValueError("chat_request must not be empty or None")
        if chat_manager is None:
            raise ValueError("chat_manager must not be None")

        chat_request_typed: ChatRequest = ChatRequest.model_construct(**chat_request)

        return await self._chat_completions(
            request=request,
            chat_request_wrapper=ChatCompletionApiRequestWrapper(chat_request_typed),
            chat_manager=chat_manager,
            token_reader=token_reader,
            auth_manager=auth_manager,
            environment_variables=environment_variables,
        )

    # noinspection PyMethodMayBeStatic
    async def chat_responses(
        self,
        request: Request,
        chat_request: Dict[str, Any],
        chat_manager: Annotated[
            ChatCompletionManager, Depends(Inject(ChatCompletionManager))
        ],
        token_reader: Annotated[TokenReader, Depends(Inject(TokenReader))],
        auth_manager: Annotated[AuthManager, Depends(Inject(AuthManager))],
        environment_variables: Annotated[
            LanguageModelGatewayEnvironmentVariables,
            Depends(Inject(LanguageModelGatewayEnvironmentVariables)),
        ],
    ) -> StreamingResponse | JSONResponse:
        """
        Chat completions endpoint. chat_manager is injected by FastAPI.

        Args:
            request: The incoming request
            chat_request: The chat request data
            chat_manager: Injected chat manager instance
            token_reader: Injected token reader instance
            auth_manager: Injected auth manager instance
            environment_variables: Injected environment variables instance

        Returns:
            StreamingResponse or JSONResponse

        Raises:
            HTTPException: For various error conditions
        """
        if not chat_request:
            raise ValueError("chat_request must not be empty or None")
        if chat_manager is None:
            raise ValueError("chat_manager must not be None")

        chat_request_typed: ResponsesRequest = ResponsesRequest.model_construct(
            **chat_request
        )

        return await self._chat_completions(
            request=request,
            chat_request_wrapper=ResponsesApiRequestWrapper(
                chat_request=chat_request_typed
            ),
            chat_manager=chat_manager,
            token_reader=token_reader,
            auth_manager=auth_manager,
            environment_variables=environment_variables,
        )

    async def _chat_completions(
        self,
        request: Request,
        chat_request_wrapper: ChatRequestWrapper,
        chat_manager: Annotated[
            ChatCompletionManager, Depends(Inject(ChatCompletionManager))
        ],
        token_reader: Annotated[TokenReader, Depends(Inject(TokenReader))],
        auth_manager: Annotated[AuthManager, Depends(Inject(AuthManager))],
        environment_variables: Annotated[
            LanguageModelGatewayEnvironmentVariables,
            Depends(Inject(LanguageModelGatewayEnvironmentVariables)),
        ],
    ) -> StreamingResponse | JSONResponse:
        try:
            auth_information = await self.read_auth_information(
                environment_variables=environment_variables,
                request=request,
                token_reader=token_reader,
                auth_manager=auth_manager,
            )

            return await chat_manager.chat_completions(
                # convert headers to lowercase to match OpenAI API expectations
                headers={k.lower(): v for k, v in request.headers.items()},
                chat_request_wrapper=chat_request_wrapper,
                auth_information=auth_information,
            )
        except* TokenRetrievalError as e:
            logger.exception(e, stack_info=True)
            # return JSONResponse(content=f"Error retrieving AWS token: {e}", status_code=500)
            raise HTTPException(
                status_code=500,
                detail=f"Error retrieving AWS token: {e}.  If running on developer machines, run `aws sso login --profile [profile_name]` to get the token.",
            )
        except* AuthorizationNeededException as e:
            logger.exception(e, stack_info=True)
            raise HTTPException(
                status_code=401,
                detail="Your login has expired. Please log in again.",
            )
        except* ConnectionError as e:
            call_stack = traceback.format_exc()
            error_detail: ErrorDetail = {
                "message": "Service connection error",
                "timestamp": datetime.now().isoformat(),
                "trace_id": "",
                "call_stack": call_stack,
            }
            logger.exception(e, stack_info=True)
            raise HTTPException(status_code=503, detail=error_detail)

        except* ValueError as e:
            call_stack = traceback.format_exc()
            error_detail = {
                "message": str(e),
                "timestamp": datetime.now().isoformat(),
                "trace_id": "",
                "call_stack": call_stack,
            }
            logger.exception(e, stack_info=True)
            raise HTTPException(status_code=400, detail=error_detail)

        except* Exception as e:
            call_stack = traceback.format_exc()
            error_detail = {
                "message": "Internal server error",
                "timestamp": datetime.now().isoformat(),
                "trace_id": "",
                "call_stack": call_stack,
            }
            logger.exception(e, stack_info=True)
            raise HTTPException(status_code=500, detail=error_detail)

    # noinspection PyMethodMayBeStatic
    async def read_auth_information(
        self,
        *,
        environment_variables: LanguageModelGatewayEnvironmentVariables,
        request: Request,
        token_reader: TokenReader,
        auth_manager: AuthManager,
    ) -> AuthInformation:
        """
        Reads the authentication information from the request headers and verifies the token if present.
        Args:
            environment_variables: The environment variables instance
            request: The incoming request
            token_reader: The token reader instance
            auth_manager: The authentication manager instance
        Returns:
            AuthInformation instance with the extracted information
        """

        # set default values first and the override if we have a valid token
        auth_information: AuthInformation = AuthInformation(
            redirect_uri=environment_variables.auth_redirect_uri
            or str(request.url_for("auth_callback")),
            claims=None,
            expires_at=None,
            audience=None,
            email=None,
            subject=None,
            user_name=None,
        )
        auth_header = request.headers.get("Authorization")
        if auth_header:
            token: str | None = token_reader.extract_token(
                authorization_header=auth_header
            )
            token_item: Token | None = None
            if (
                token and token in ["bedrock", "fake-api-key"]
                # fake-api-key and "bedrock" are special values to bypass auth for local dev and bedrock access
            ):
                token_item = None
            elif token:
                token_item = await token_reader.verify_token_async(token=token)

            if token_item is not None:
                auth_information.claims = token_item.claims
                auth_information.expires_at = token_item.expires
                auth_information.audience = token_item.audience
                # Okta sets email in subject sometimes, so check both
                auth_information.email = token_item.email or (
                    token_item.subject
                    if token_item.subject and "@" in token_item.subject
                    else None
                )
                auth_information.subject = token_item.subject or token_item.email
                auth_information.user_name = token_item.name
            else:
                # read information from headers if present
                if "x-openwebui-user-id" in request.headers:
                    auth_information.subject = request.headers["x-openwebui-user-id"]
                if "x-openwebui-user-email" in request.headers:
                    auth_information.email = request.headers["x-openwebui-user-email"]
                if "x-openwebui-user-name" in request.headers:
                    auth_information.user_name = request.headers[
                        "x-openwebui-user-name"
                    ]
        return auth_information

    def get_router(self) -> APIRouter:
        """Get the configured router"""
        return self.router
