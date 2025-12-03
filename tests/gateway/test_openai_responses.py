import httpx
import pytest
from oidcauthlib.container.interfaces import IContainer
from openai import AsyncOpenAI
from openai.types.responses import (
    EasyInputMessageParam,
    Response,
    ResponseOutputMessage,
    ResponseInputParam,
    ResponseOutputText,
)

from language_model_gateway.configs.config_schema import ChatModelConfig, ModelConfig
from language_model_gateway.gateway.utilities.cache.config_expiring_cache import (
    ConfigExpiringCache,
)


@pytest.mark.asyncio
async def test_openai_responses(
    async_client: httpx.AsyncClient, test_container: IContainer
) -> None:
    print("")
    # Always set the Test Model in the cache
    model_configuration_cache: ConfigExpiringCache = test_container.resolve(
        ConfigExpiringCache
    )
    await model_configuration_cache.set(
        [
            ChatModelConfig(
                id="test_model",
                name="Test Model",
                description="General Purpose",
                type="langchain",
                model=ModelConfig(provider="ollama"),
            )
        ]
    )

    client = AsyncOpenAI(
        api_key="fake-api-key",
        base_url="http://localhost:5000/api/v1",
        http_client=async_client,
    )

    prompt: EasyInputMessageParam = {
        "content": "I'm 60 years old and have been programming for 5 days.",
        "role": "user",
        "type": "message",
    }
    response: Response = await client.responses.create(
        model="test_model",
        input=[prompt],
        max_output_tokens=20,
    )
    content: str = response.output_text if response.output else ""
    assert content is not None
    print(content)

    prompt = {
        "content": "let’s talk about football",
        "role": "user",
        "type": "message",
    }
    response = await client.responses.create(
        model="test_model",
        input=[prompt],
        max_output_tokens=20,
    )
    content = response.output_text if response.output else ""
    assert content is not None

    prompt = {
        "content": "look up my user profile",
        "role": "user",
        "type": "message",
    }
    response = await client.responses.create(
        model="test_model",
        input=[prompt],
        max_output_tokens=20,
    )
    content = response.output_text if response.output else ""
    assert content is not None


@pytest.mark.asyncio
async def test_openai_responses_with_history(
    async_client: httpx.AsyncClient, test_container: IContainer
) -> None:
    print("")
    # Always set the Test Model in the cache
    model_configuration_cache: ConfigExpiringCache = test_container.resolve(
        ConfigExpiringCache
    )
    await model_configuration_cache.set(
        [
            ChatModelConfig(
                id="test_model",
                name="Test Model",
                description="General Purpose",
                type="langchain",
                model=ModelConfig(provider="ollama"),
            )
        ]
    )

    client = AsyncOpenAI(
        api_key="fake-api-key",
        base_url="http://localhost:5000/api/v1",
        http_client=async_client,
    )

    # Step 1: Initial context
    message1: EasyInputMessageParam = {
        "role": "user",
        "content": "What is the capital of France?",
    }
    context: ResponseInputParam = [message1]
    res1: Response = await client.responses.create(
        model="Test Model",
        input=context,
        max_output_tokens=20,
    )
    print("========  Response 1 ======")
    print(res1)
    print("====== End of Response 1 ======")
    content1: str = res1.output_text if res1.output_text else ""
    assert content1 is not None
    print("======= Response 1 Content =======")
    print(content1)
    print("==== End of Response 1 Content ====")
    # Step 2: Append first response's output to context
    if res1.output:
        assert isinstance(res1.output[-1], ResponseOutputMessage)
        last_output: ResponseOutputMessage = res1.output[-1]
        assert last_output.content
        assert isinstance(last_output.content, ResponseOutputText)
        # last_output_content_: str = last_output.content[0].text
        message_out: EasyInputMessageParam = {
            "role": "assistant",
            "content": "Paris",
            "type": "message",
        }
        context.append(message_out)
    # Step 3: Add next user message
    message2: EasyInputMessageParam = {
        "role": "user",
        "content": "And its population?",
        "type": "message",
    }
    context.append(message2)

    res2: Response = await client.responses.create(
        model="Test Model",
        input=context,
        max_output_tokens=200,
    )
    print("========  Response 2 ======")
    print(res2)
    print("====== End of Response 2 ======")
    content2: str = res2.output_text if res2.output_text else ""
    assert content2 is not None
    print("======= Response 2 Content =======")
    print(content2)
    print("==== End of Response 2 Content ====")
    assert "Paris" in content1 or "Paris" in content2
