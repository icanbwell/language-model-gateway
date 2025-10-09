from typing import Literal, Optional, Union, List, Dict, Iterable

import httpx

# noinspection PyProtectedMember
from openai._types import Headers, Query, Body
from openai.types import ChatModel
from openai.types.chat import (
    ChatCompletionMessageParam,
    ChatCompletionAudioParam,
    completion_create_params,
    ChatCompletionModality,
    ChatCompletionPredictionContentParam,
    ChatCompletionStreamOptionsParam,
    ChatCompletionToolChoiceOptionParam,
    ChatCompletionToolParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionContentPartTextParam,
    ChatCompletionUserMessageParam,
    ChatCompletionAssistantMessageParam,
)
from pydantic import BaseModel, ConfigDict, Field


# This class is copied from openai package: openai/resources/chat/completions.py
# and converted to Pydantic model


class ChatRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid"  # Prevents any additional properties
    )
    messages: List[ChatCompletionMessageParam] = Field(
        ..., description="The messages to generate chat completions for."
    )
    model: Optional[Union[str, ChatModel]] = None
    audio: Optional[ChatCompletionAudioParam] = None
    frequency_penalty: Optional[float] = None
    function_call: Optional[completion_create_params.FunctionCall] = None
    functions: Optional[List[completion_create_params.Function]] = None
    logit_bias: Optional[Dict[str, int]] = None
    logprobs: Optional[bool] = None
    max_completion_tokens: Optional[int] = None
    max_tokens: Optional[int] = None
    metadata: Optional[Dict[str, str]] = None
    modalities: Optional[List[ChatCompletionModality]] = None
    n: Optional[int] = None
    parallel_tool_calls: Optional[bool] = None
    prediction: Optional[ChatCompletionPredictionContentParam] = None
    presence_penalty: Optional[float] = None
    response_format: Optional[completion_create_params.ResponseFormat] = None
    seed: Optional[int] = None
    service_tier: Optional[Literal["auto", "default"]] = None
    stop: Optional[Union[str, List[str]]] = None
    store: Optional[bool] = None
    stream: Optional[Union[Literal[False], Literal[True]]] = None
    stream_options: Optional[ChatCompletionStreamOptionsParam] = None
    temperature: Optional[float] = None
    tool_choice: Optional[ChatCompletionToolChoiceOptionParam] = None
    tools: Optional[List[ChatCompletionToolParam]] = None
    top_logprobs: Optional[int] = None
    top_p: Optional[float] = None
    user: Optional[str] = None
    extra_headers: Optional[Headers] = None
    extra_query: Optional[Query] = None
    extra_body: Optional[Body] = None
    timeout: Optional[Union[float, httpx.Timeout]] = None


ROLE_TYPES = Literal["system", "user", "assistant", "tool"]

INCOMING_MESSAGE_TYPES = str | Iterable[ChatCompletionContentPartTextParam]

IncomingSystemMessage = ChatCompletionSystemMessageParam

IncomingHumanMessage = ChatCompletionUserMessageParam

IncomingAssistantMessage = ChatCompletionAssistantMessageParam
