from datetime import datetime
import logging
import traceback
from enum import Enum
from typing import Annotated, Dict, Any, TypedDict, cast, Sequence

from botocore.exceptions import TokenRetrievalError
from fastapi import APIRouter, Depends, HTTPException
from starlette.requests import Request
from starlette.responses import StreamingResponse, JSONResponse
from fastapi import params

from language_model_gateway.gateway.api_container import get_chat_manager
from language_model_gateway.gateway.managers.chat_completion_manager import (
    ChatCompletionManager,
)
from language_model_gateway.gateway.schema.openai.completions import ChatRequest

logger = logging.getLogger(__name__)


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

    # noinspection PyMethodMayBeStatic
    async def chat_completions(
        self,
        request: Request,
        chat_request: Dict[str, Any],
        chat_manager: Annotated[ChatCompletionManager, Depends(get_chat_manager)],
    ) -> StreamingResponse | JSONResponse:
        """
        Chat completions endpoint. chat_manager is injected by FastAPI.

        Args:
            request: The incoming request
            chat_request: The chat request data
            chat_manager: Injected chat manager instance

        Returns:
            StreamingResponse or JSONResponse

        Raises:
            HTTPException: For various error conditions
        """
        assert chat_request
        assert chat_manager

        try:
            return await chat_manager.chat_completions(
                # convert headers to lowercase to match OpenAI API expectations
                headers={k.lower(): v for k, v in request.headers.items()},
                chat_request=cast(ChatRequest, chat_request),
            )
        except* TokenRetrievalError as e:
            logger.exception(e, stack_info=True)
            # return JSONResponse(content=f"Error retrieving AWS token: {e}", status_code=500)
            raise HTTPException(
                status_code=500,
                detail=f"Error retrieving AWS token: {e}.  If running on developer machines, run `aws sso login --profile [profile_name]` to get the token.",
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

    def get_router(self) -> APIRouter:
        """Get the configured router"""
        return self.router
