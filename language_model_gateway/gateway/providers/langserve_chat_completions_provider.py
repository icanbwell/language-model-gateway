# import json
# import logging
# import random
# import time
# from os import environ
# from typing import AsyncGenerator, cast, List, Any, Dict, Optional
#
# import httpx
# from httpx import Response
# from httpx_sse import aconnect_sse, ServerSentEvent
# from openai.types import CompletionUsage
# from openai.types.chat import (
#     ChatCompletionChunk,
#     ChatCompletionMessageParam,
#     ChatCompletionUserMessageParam,
#     ChatCompletion,
#     ChatCompletionMessage,
# )
# from openai.types.chat.chat_completion import Choice
# from openai.types.chat.chat_completion_chunk import ChoiceDelta, Choice as ChunkChoice
# from starlette.responses import StreamingResponse, JSONResponse
#
# from language_model_gateway.configs.config_schema import ChatModelConfig
# from language_model_gateway.gateway.providers.base_chat_completions_provider import (
#     BaseChatCompletionsProvider,
# )
# from language_model_gateway.gateway.schema.openai.completions import ChatRequest
#
# logger = logging.getLogger(__file__)
#
#
# class LangServeChatCompletionsProvider(BaseChatCompletionsProvider):
#     async def chat_completions(
#         self,
#         *,
#         model_config: ChatModelConfig,
#         headers: Dict[str, str],
#         chat_request: ChatRequest,
#     ) -> StreamingResponse | JSONResponse:
#         request_id = random.randint(1, 1000)
#         logger.info(f"Received request {request_id}: {chat_request}")
#
#         response_context: str
#         if chat_request["messages"]:
#             request_messages: List[ChatCompletionMessageParam] = [
#                 m for m in chat_request["messages"]
#             ]
#             resp_content = cast(
#                 str,
#                 cast(ChatCompletionUserMessageParam, request_messages[-1])["content"],
#             )
#         else:
#             resp_content = "As a mock AI Assistant, I can only echo your last message, but there wasn't one!"
#
#         if resp_content == "dummy":
#             if chat_request.get("stream"):
#                 logger.info(f"Streaming response {request_id}")
#                 return StreamingResponse(
#                     LangServeChatCompletionsProvider._resp_async_generator(
#                         request_model=chat_request["model"], text_resp=resp_content
#                     ),
#                     media_type="text/event-stream",
#                 )
#             response_dict: ChatCompletion = ChatCompletion(
#                 id="1337",
#                 created=int(time.time()),
#                 model=chat_request["model"],
#                 choices=[
#                     Choice(
#                         index=0,
#                         message=ChatCompletionMessage(
#                             role="assistant", content=resp_content
#                         ),
#                         finish_reason="stop",
#                     )
#                 ],
#                 usage=CompletionUsage(
#                     prompt_tokens=0, completion_tokens=0, total_tokens=0
#                 ),
#                 object="chat.completion",
#             )
#             logger.info(f"Non-streaming response {request_id}: {response_dict}")
#             return JSONResponse(content=response_dict.model_dump())
#         else:
#             return await self.call_ai_agent(
#                 request=chat_request, request_id=str(request_id)
#             )
#
#     @staticmethod
#     async def _resp_async_generator(
#         *, request_model: str, text_resp: str
#     ) -> AsyncGenerator[str, None]:
#         tokens = text_resp.split(" ")
#         for i, token in enumerate(tokens):
#             chunk: ChatCompletionChunk = ChatCompletionChunk(
#                 id=str(i),
#                 created=int(time.time()),
#                 model=request_model,
#                 choices=[
#                     ChunkChoice(
#                         index=0,
#                         delta=ChoiceDelta(role="assistant", content=token + " "),
#                     )
#                 ],
#                 usage=CompletionUsage(
#                     prompt_tokens=0, completion_tokens=0, total_tokens=0
#                 ),
#                 object="chat.completion.chunk",
#             )
#             yield f"data: {json.dumps(chunk.model_dump())}\n\n"
#         yield "data: [DONE]\n\n"
#
#     @staticmethod
#     async def _stream_resp_async_generator(
#         *,
#         request_id: str,
#         agent_url: str,
#         test_data: Dict[str, Any],
#         request_model: str,
#     ) -> AsyncGenerator[str, None]:
#
#         logger.info(f"Streaming response {request_id} from agent")
#         async with httpx.AsyncClient(base_url=agent_url) as client:
#             async with aconnect_sse(
#                 client,
#                 "POST",
#                 "/stream",
#                 json={"input": test_data},
#                 timeout=60 * 60,
#             ) as event_source:
#                 i = 0
#                 sse: ServerSentEvent
#                 async for sse in event_source.aiter_sse():
#                     event: str = sse.event
#                     data: str = sse.data
#                     i += 1
#
#                     logger.info(
#                         f"----- Received data from stream {i} {event} {type(data)} ------"
#                     )
#                     logger.info(data)
#                     logger.info(
#                         f"----- End data from stream {i} {event} {type(data)} ------"
#                     )
#
#                     if event == "data" and data:
#                         response_json: Dict[str, Any] = json.loads(data)
#                         if "output" in response_json:
#                             output_responses: List[Dict[str, Any]] = response_json[
#                                 "output"
#                             ]
#                             if len(output_responses) >= 0:
#                                 response_text: str = output_responses[0]["text"]
#                                 chunk: ChatCompletionChunk = ChatCompletionChunk(
#                                     id=str(i),
#                                     created=int(time.time()),
#                                     model=request_model,
#                                     choices=[
#                                         ChunkChoice(
#                                             index=0,
#                                             delta=ChoiceDelta(
#                                                 role="assistant", content=response_text
#                                             ),
#                                         )
#                                     ],
#                                     usage=CompletionUsage(
#                                         prompt_tokens=0,
#                                         completion_tokens=0,
#                                         total_tokens=0,
#                                     ),
#                                     object="chat.completion.chunk",
#                                 )
#                                 yield f"data: {json.dumps(chunk.model_dump())}\n\n"
#                 yield "data: [DONE]\n\n"
#
#     async def call_ai_agent(
#         self, *, request: ChatRequest, request_id: str
#     ) -> StreamingResponse | JSONResponse:
#         messages: List[ChatCompletionMessageParam] = [m for m in request["messages"]]
#         input_text: str = cast(
#             str, cast(ChatCompletionUserMessageParam, messages[-1])["content"]
#         )
#         chat_history: List[ChatCompletionMessageParam] = messages
#         return await self.call_agent_with_input(
#             chat_history=[c for c in chat_history],
#             input_text=input_text,
#             model=request["model"],
#             agent_url=environ["AGENT_URL"],
#             patient_id=environ["DEFAULT_PATIENT_ID"],
#             request_id=request_id,
#             stream_request=True if request.get("stream") else False,
#         )
#
#     @staticmethod
#     async def call_agent_with_input(
#         *,
#         chat_history: List[ChatCompletionMessageParam],
#         input_text: str,
#         model: str,
#         agent_url: str,
#         patient_id: str,
#         request_id: str,
#         stream_request: Optional[bool],
#     ) -> StreamingResponse | JSONResponse:
#         assert agent_url
#         assert patient_id
#         assert input_text
#         assert isinstance(chat_history, list)
#
#         # NOTE: If uncommenting, replace asserts with exceptions for production use:
#         if not agent_url:
#             raise ValueError("agent_url must not be empty")
#         if not patient_id:
#             raise ValueError("patient_id must not be empty")
#         if not input_text:
#             raise ValueError("input_text must not be empty")
#         if not isinstance(chat_history, list):
#             raise TypeError("chat_history must be a list")
#
#         test_data = {
#             "input": input_text,
#             "patient_id": patient_id,
#             "chat_history": chat_history,
#         }
#         if stream_request:
#             return StreamingResponse(
#                 await LangServeChatCompletionsProvider.get_streaming_response_async(
#                     model=model,
#                     agent_url=agent_url,
#                     request_id=request_id,
#                     test_data=test_data,
#                 ),
#                 media_type="text/event-stream",
#             )
#
#         async with httpx.AsyncClient(base_url=agent_url) as client:
#             agent_response: Response = await client.post(
#                 "/invoke", json={"input": test_data}, timeout=60 * 60
#             )
#
#             response_text: str = agent_response.text
#             try:
#                 response_dict: Dict[str, Any] = agent_response.json()
#             except json.JSONDecodeError:
#                 response_dict = {
#                     "output": {
#                         "output": [
#                             {"text": f"{agent_response.status_code} {response_text}"},
#                         ]
#                     }
#                 }
#
#             # NOTE: If uncommenting, replace asserts with exceptions for production use:
#             if agent_response.status_code != 200:
#                 raise ValueError(f"agent_response.status_code must be 200, got {agent_response.status_code}")
#             if "output" not in response_dict:
#                 raise ValueError('"output" key missing in response_dict')
#             if len(outputs) != 1:
#                 raise ValueError(f"outputs must have length 1, got {len(outputs)}")
#
#             output_dict: Dict[str, Any] = response_dict["output"]
#             outputs: List[Dict[str, Any]] = output_dict["output"]
#             assert len(outputs) == 1
#             output_text: str = outputs[0]["text"]
#
#             response: ChatCompletion = ChatCompletion(
#                 id="1337",
#                 created=int(time.time()),
#                 model=model,
#                 choices=[
#                     Choice(
#                         index=0,
#                         message=ChatCompletionMessage(
#                             role="assistant", content=output_text
#                         ),
#                         finish_reason="stop",
#                     )
#                 ],
#                 usage=CompletionUsage(
#                     prompt_tokens=0, completion_tokens=0, total_tokens=0
#                 ),
#                 object="chat.completion",
#             )
#             logger.info(f"Non-streaming response {request_id}: {response}")
#             return JSONResponse(content=response.model_dump())
#
#     @staticmethod
#     async def get_streaming_response_async(
#         *, agent_url: str, model: str, request_id: str, test_data: Dict[str, Any]
#     ) -> AsyncGenerator[str, None]:
#         logger.info(f"Streaming response {request_id} from agent")
#         generator: AsyncGenerator[str, None] = (
#             LangServeChatCompletionsProvider._stream_resp_async_generator(
#                 request_model=model,
#                 agent_url=agent_url,
#                 test_data=test_data,
#                 request_id=request_id,
#             )
#         )
#         return generator
