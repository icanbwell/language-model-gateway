from typing import Optional

import httpx
from oidcauthlib.container.interfaces import IContainer
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion, ChatCompletionUserMessageParam

from language_model_gateway.configs.config_schema import (
    ChatModelConfig,
    ModelConfig,
    AgentConfig,
    PromptConfig,
)
from language_model_gateway.gateway.utilities.cache.config_expiring_cache import (
    ConfigExpiringCache,
)


async def test_chat_anthropic_with_pdf_scraping(
    async_client: httpx.AsyncClient, test_container: IContainer
) -> None:
    # Always set the Test Model in the cache
    model_configuration_cache: ConfigExpiringCache = test_container.resolve(
        ConfigExpiringCache
    )
    await model_configuration_cache.set(
        [
            ChatModelConfig(
                id="test_model",
                name="Test Model",
                description="PDF/Web Scraping Model",
                type="langchain",
                model=ModelConfig(provider="ollama"),
                system_prompts=[
                    PromptConfig(
                        role="system",
                        content="You are an assistant that parses web pages and PDFs. Let’s think step by step and take your time to get the right answer."
                        " Try the get_web_page tool first and if you don't get the answer then use the scraping_bee_web_scraper tool.",
                    )
                ],
                tools=[
                    AgentConfig(name="google_search"),
                    AgentConfig(name="get_web_page"),
                    AgentConfig(name="pdf_text_extractor"),
                ],
            )
        ]
    )

    # init client and connect to localhost server
    client = AsyncOpenAI(
        api_key="fake-api-key",
        base_url="http://localhost:5000/api/v1",
        http_client=async_client,
    )

    # call API
    message1: ChatCompletionUserMessageParam = {
        "role": "user",
        "content": "Get the definition of Prevention TaskForce from"
        " https://www.uspreventiveservicestaskforce.org/files/preventiontaskforce_data_api_wi_wlink.pdf",
    }
    chat_completion: ChatCompletion = await client.chat.completions.create(
        messages=[message1],
        model="Test Model",
    )

    print(chat_completion)
    # print the top "choice"
    content: Optional[str] = "\n".join(
        choice.message.content or "" for choice in chat_completion.choices
    )
    assert content is not None
    print(content)
    assert "USPSTF" in content


async def test_chat_anthropic_with_pdf_ocr_scraping(
    async_client: httpx.AsyncClient, test_container: IContainer
) -> None:
    # Always set the Test Model in the cache
    model_configuration_cache: ConfigExpiringCache = test_container.resolve(
        ConfigExpiringCache
    )
    await model_configuration_cache.set(
        [
            ChatModelConfig(
                id="test_model",
                name="Test Model",
                description="PDF/Web Scraping Model",
                type="langchain",
                model=ModelConfig(provider="ollama"),
                system_prompts=[
                    PromptConfig(
                        role="system",
                        content="You are an assistant that parses web pages and PDFs."
                        " Let’s think step by step and take your time to get the right answer."
                        " Try the get_web_page tool first and if you don't get the answer then use the scraping_bee_web_scraper tool.",
                    )
                ],
                tools=[
                    AgentConfig(name="google_search"),
                    AgentConfig(name="get_web_page"),
                    AgentConfig(name="pdf_text_extractor"),
                ],
            )
        ]
    )

    # init client and connect to localhost server
    client = AsyncOpenAI(
        api_key="fake-api-key",
        base_url="http://localhost:5000/api/v1",
        http_client=async_client,
    )

    # call API
    message1: ChatCompletionUserMessageParam = {
        "role": "user",
        "content": "Get the debt to capitalization rate from https://emma.msrb.org/P21807566.pdf",
    }
    chat_completion: ChatCompletion = await client.chat.completions.create(
        messages=[message1],
        model="Test Model",
    )

    print(chat_completion)
    # print the top "choice"
    content: Optional[str] = "\n".join(
        choice.message.content or "" for choice in chat_completion.choices
    )
    assert content is not None
    print(content)
    assert "23%" in content
