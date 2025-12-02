from datetime import datetime, UTC
from typing import Literal, Union, override, Optional, List, Any

from langchain_core.messages import AnyMessage
from langchain_core.messages.ai import UsageMetadata
from openai.types.responses import (
    ResponseInputParam,
    EasyInputMessageParam,
    ResponseTextDeltaEvent,
    ResponseTextDoneEvent,
    Response,
    ResponseOutputItem,
    ResponseOutputMessage,
    ResponseOutputText,
    ResponseOutputRefusal,
)

from language_model_gateway.configs.config_schema import AgentConfig
from language_model_gateway.gateway.schema.openai.responses import ResponsesRequest
from language_model_gateway.gateway.structures.openai.message.chat_message_wrapper import (
    ChatMessageWrapper,
)
from language_model_gateway.gateway.structures.openai.message.responses_api_message_wrapper import (
    ResponsesApiMessageWrapper,
)
from language_model_gateway.gateway.structures.openai.request.chat_request_wrapper import (
    ChatRequestWrapper,
)


class ResponsesApiRequestWrapper(ChatRequestWrapper):
    def __init__(self, chat_request: ResponsesRequest) -> None:
        """
        Wraps an OpenAI /responses API request and provides a unified interface so the code can use it

        """
        self.request: ResponsesRequest = chat_request

        self._messages: list[ChatMessageWrapper] = self.convert_from_responses_input(
            input_=self.request.input
        )

    @staticmethod
    def convert_from_responses_input(
        *, input_: Union[str, ResponseInputParam]
    ) -> list[ChatMessageWrapper]:
        if isinstance(input_, str):
            return [
                ResponsesApiMessageWrapper(
                    input_=EasyInputMessageParam(role="user", content=input_)
                )
            ]
        elif isinstance(input_, list):
            return [ResponsesApiMessageWrapper(input_=item) for item in input_]
        else:
            return []

    @property
    @override
    def model(self) -> str:
        return self.request.model

    @property  # type: ignore[explicit-override]
    @override
    def messages(self) -> list[ChatMessageWrapper]:
        return self._messages

    @messages.setter
    def messages(self, value: list[ChatMessageWrapper]) -> None:
        self._messages = value

    @override
    def append_message(self, *, message: ChatMessageWrapper) -> None:
        self._messages.append(message)

    @override
    def create_system_message(self, *, content: str) -> ChatMessageWrapper:
        return ResponsesApiMessageWrapper.create_system_message(content=content)

    @override
    @property
    def stream(self) -> Literal[False, True] | None | bool:
        return self.request.stream

    @override
    @property
    def response_format(self) -> Literal["text", "json_object", "json_schema"] | None:
        return "json_object"  # in case of ResponsesRequest, we always use JSON object format

    @override
    @property
    def response_json_schema(self) -> str | None:
        return None  # Not applicable for ResponsesRequest

    @override
    def create_sse_message(
        self,
        *,
        request_id: str,
        content: str | None,
        usage_metadata: UsageMetadata | None,
    ) -> str:
        # Format a single SSE message chunk for streaming
        if content is None:
            return ""

        message: ResponseTextDeltaEvent = ResponseTextDeltaEvent(
            item_id=request_id,
            content_index=0,
            output_index=len(self._messages),
            delta=content,
            type="response.output_text.delta",
            sequence_number=len(self._messages),
            logprobs=[],
        )
        return f"data: {message.model_dump_json()}\n\n"

    @override
    def create_final_sse_message(
        self, *, request_id: str, usage_metadata: UsageMetadata | None
    ) -> str:
        # Format the final SSE message chunk
        message: ResponseTextDoneEvent = ResponseTextDoneEvent(
            item_id=request_id,
            content_index=0,
            output_index=len(self._messages),
            type="response.output_text.done",
            sequence_number=len(self._messages),
            logprobs=[],
            text="",
        )
        return f"data: {message.model_dump_json()}\n\n"

    @staticmethod
    def convert_message_content(
        input_content: str | list[str | dict[str, Any]],
    ) -> list[ResponseOutputText | ResponseOutputRefusal]:
        if isinstance(input_content, str):
            return [
                ResponseOutputText(
                    text=input_content, type="output_text", annotations=[]
                )
            ]
        elif isinstance(input_content, list):
            output_texts: list[ResponseOutputText | ResponseOutputRefusal] = []
            for item in input_content:
                if isinstance(item, str):
                    output_texts.append(
                        ResponseOutputText(
                            text=item, type="output_text", annotations=[]
                        )
                    )
                elif isinstance(item, dict):
                    output_texts.append(ResponseOutputText(**item))
            return output_texts
        else:
            return []

    @override
    def create_non_streaming_response(
        self,
        *,
        request_id: str,
        json_output_requested: Optional[bool],
        responses: List[AnyMessage],
    ) -> dict[str, Any]:
        # Build a non-streaming response dict
        output: list[ResponseOutputItem] = []
        for idx, msg in enumerate(responses):
            content: str | list[str | dict[str, Any]] = msg.content
            output.append(
                ResponseOutputMessage(
                    id=str(idx),
                    content=self.convert_message_content(input_content=content),
                    role="assistant",
                    status="completed",
                    type="message",
                )
            )
        response: Response = Response(
            id=request_id,
            created_at=datetime.now(UTC).timestamp(),
            output=output,
            model=self.model,
            object="response",
            parallel_tool_calls=False,
            tools=[],
            tool_choice="auto",
        )
        # Usage metadata is not passed here, but could be added if available
        return response.model_dump(mode="json")

    @override
    def to_dict(self) -> dict[str, Any]:
        return self.request.model_dump(mode="json")

    @staticmethod
    def extract_mcp_agent_configs(
        tools_in_request: list[dict[str, Any]],
    ) -> list[AgentConfig]:
        """
        Extract AgentConfig objects for MCP tools from the tools_in_request list.
        """
        return [
            AgentConfig(
                url=tool["server_url"],
                name=tool["server_label"],
                tools=",".join(
                    [
                        t["name"] if isinstance(t, dict) and "name" in t else str(t)
                        for t in tool["allowed_tools"]
                    ]
                )
                if isinstance(tool["allowed_tools"], (list, tuple))
                else "",
                headers=tool.get("headers"),
                auth="headers",
            )
            for tool in tools_in_request
            if tool["type"] == "mcp"
            and "server_url" in tool
            and "server_label" in tool
            and "allowed_tools" in tool
        ]

    @override
    def get_tools(self) -> list[AgentConfig]:
        """
        Return a list of tools passed in the request.
        """
        tools_in_request: list[dict[str, Any]] | None = self.request.tools
        if tools_in_request is None:
            return []
        return self.extract_mcp_agent_configs(tools_in_request)
