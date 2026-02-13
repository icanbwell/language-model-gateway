import json
from typing import Dict, Optional, AsyncGenerator, override

from oidcauthlib.auth.models.auth import AuthInformation
from starlette.responses import StreamingResponse, JSONResponse

from language_model_gateway.configs.config_schema import ChatModelConfig
from language_model_gateway.gateway.providers.base_chat_completions_provider import (
    BaseChatCompletionsProvider,
)
from language_model_gateway.gateway.structures.openai.request.chat_request_wrapper import (
    ChatRequestWrapper,
)

from openai import AsyncOpenAI, AsyncStream
from openai.types.chat import ChatCompletionChunk, ChatCompletionUserMessageParam


class PassThroughChatCompletionsProvider(BaseChatCompletionsProvider):
    """
    A chat completions provider that simply passes through the request to the another chat completion API
    without any modifications or additional processing.
    This provider can be used when you want to directly forward the chat completion requests to an external API
    """

    @override
    async def chat_completions(
        self,
        *,
        model_config: ChatModelConfig,
        headers: Dict[str, str],
        chat_request_wrapper: ChatRequestWrapper,
        auth_information: AuthInformation,
    ) -> StreamingResponse | JSONResponse:
        pass_through_url: Optional[str] = model_config.url
        if pass_through_url is None:
            return JSONResponse(
                status_code=400,
                content={"error": "Pass through URL is not configured for this model."},
            )
        if model_config.model is None:
            return JSONResponse(
                status_code=400,
                content={
                    "error": "Model configuration is not provided for this model."
                },
            )
        client = AsyncOpenAI(
            api_key="fake-api-key",  # pragma: allowlist secret
            # this api key is ignored for now.  suggest setting it to something that identifies your calling code
            base_url=pass_through_url,
            # default_headers={
            #     "Authorization": f"Bearer {os.getenv('GATEWAY_TOKEN')}",
            # }
        )
        message: ChatCompletionUserMessageParam = {
            "role": "user",
            "content": "Get the address of Dr. Meggin A. Sabatino at Medstar",  # specify your prompt here
        }
        stream: AsyncStream[ChatCompletionChunk] = await client.chat.completions.create(
            messages=[message],
            model=model_config.model.model,
            # choose the task model - same as the task models in https://openwebui.services.bwell.zone/
            stream=True,  # enables streaming
        )

        async def stream_response(
            stream1: AsyncStream[ChatCompletionChunk],
        ) -> AsyncGenerator[str, None]:
            chunk: ChatCompletionChunk
            async for chunk in stream1:
                yield f"data: {json.dumps(chunk.model_dump())}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(
            content=stream_response(stream1=stream),
            media_type="text/event-stream",
        )
