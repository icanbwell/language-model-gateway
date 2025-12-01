import httpx
import pytest
from oidcauthlib.container.interfaces import IContainer
from openai import AsyncOpenAI, AsyncStream
from openai.types.responses import (
    ResponseStreamEvent,
    ResponseTextDeltaEvent,
    EasyInputMessageParam,
    ResponseInputParam,
    ResponseInputContentParam,
)

from language_model_gateway.gateway.models.model_factory import ModelFactory
from language_model_gateway.gateway.utilities.environment_reader import (
    EnvironmentReader,
)
from tests.gateway.mocks.mock_chat_model import MockChatModel
from tests.gateway.mocks.mock_model_factory import MockModelFactory


@pytest.mark.asyncio
async def test_openai_responses_streaming(
    async_client: httpx.AsyncClient, test_container: IContainer
) -> None:
    print("")

    if not EnvironmentReader.is_environment_variable_set("RUN_TESTS_WITH_REAL_LLM"):
        test_container.singleton(
            ModelFactory,
            lambda c: MockModelFactory(
                fn_get_model=lambda chat_model_config: MockChatModel(
                    fn_get_response=lambda messages: "His first name is Barack"
                )
            ),
        )

    client = AsyncOpenAI(
        api_key="fake-api-key",
        base_url="http://localhost:5000/api/v1",
        http_client=async_client,
    )

    prompt: EasyInputMessageParam = {
        "content": "what is the first name of Obama?",
        "role": "user",
        "type": "message",
    }
    stream: AsyncStream[ResponseStreamEvent] = await client.responses.create(
        model="General Purpose",
        input=[prompt],
        stream=True,
        max_output_tokens=20,
    )
    content: str = ""
    i: int = 0
    chunk: ResponseStreamEvent
    async for chunk in stream:
        i += 1
        print(f"======== Chunk {i} ========")
        delta_content = (
            chunk.delta if isinstance(chunk, ResponseTextDeltaEvent) else None
        )
        content += delta_content or ""
        print(delta_content or "")
        print(f"\n{chunk}\n")
        print(f"====== End of Chunk {i} ======")

    print("======== Final Content ========")
    print(content)
    print("====== End of Final Content ======")
    assert "Barack" in content


async def test_responses_with_history_streaming(
    async_client: httpx.AsyncClient, test_container: IContainer
) -> None:
    """Test streaming responses with conversation history."""
    print("")

    if not EnvironmentReader.is_environment_variable_set("RUN_TESTS_WITH_REAL_LLM"):
        test_container.singleton(
            ModelFactory,
            lambda c: MockModelFactory(
                fn_get_model=lambda chat_model_config: MockChatModel(
                    fn_get_response=lambda messages: "His first name is Barack"
                )
            ),
        )

    client: AsyncOpenAI = AsyncOpenAI(
        api_key="fake-api-key",
        base_url="http://localhost:5000/api/v1",
        http_client=async_client,
    )

    # Define the conversation flow
    prompts: list[EasyInputMessageParam] = [
        {
            "content": "Who was the 44th president of United States?",
            "role": "user",
            "type": "message",
        },
        {
            "content": "Barack Obama",
            "role": "assistant",
            "type": "message",
        },
        {
            "content": "what is his first name?",
            "role": "user",
            "type": "message",
        },
    ]

    messages_and_answers: list[dict[str, str | list[ResponseInputContentParam]]] = []
    conversation_history: ResponseInputParam = []

    prompt: EasyInputMessageParam
    for prompt in prompts:
        # Add current message to history
        conversation_history.append(prompt)

        # Only process user messages (skip assistant messages as they're just history)
        if prompt["role"] != "user":
            continue

        # Send the full conversation history up to this point
        stream: AsyncStream[ResponseStreamEvent] = await client.responses.create(
            model="General Purpose",
            input=conversation_history,  # Pass the full history including current user message
            stream=True,
            max_output_tokens=20,
        )

        content: str = ""
        i: int = 0
        chunk: ResponseStreamEvent

        async for chunk in stream:
            i += 1
            delta_content: str | None = (
                chunk.delta if isinstance(chunk, ResponseTextDeltaEvent) else None
            )
            content += delta_content or ""

        messages_and_answers.append({"prompt": prompt["content"], "answer": content})

        # Add the assistant's response to history for next iteration
        assistant_message: EasyInputMessageParam = {
            "content": content,
            "role": "assistant",
            "type": "message",
        }
        conversation_history.append(assistant_message)

    # Print results
    for idx, entry in enumerate(messages_and_answers):
        print(f"======== Message {idx + 1} ========")
        print(f"Prompt: {entry['prompt']}")
        print(f"Answer: {entry['answer']}")
        print(f"====== End of Message {idx + 1} ======")

    # Verify that at least one response contains "Barack"
    assert any("Barack" in entry["answer"] for entry in messages_and_answers), (
        "Expected at least one response to contain 'Barack'"
    )
