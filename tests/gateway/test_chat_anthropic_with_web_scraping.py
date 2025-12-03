from typing import Optional

import httpx
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion

from language_model_gateway.configs.config_schema import (
    ChatModelConfig,
    ModelConfig,
    AgentConfig,
    PromptConfig,
)
from language_model_gateway.gateway.utilities.cache.config_expiring_cache import (
    ConfigExpiringCache,
)
from oidcauthlib.container.interfaces import IContainer


async def test_chat_anthropic_with_web_scraping(
    async_client: httpx.AsyncClient, test_container: IContainer
) -> None:
    # set the model configuration for this test
    model_configuration_cache: ConfigExpiringCache = test_container.resolve(
        ConfigExpiringCache
    )
    await model_configuration_cache.set(
        [
            ChatModelConfig(
                id="parse_web_page",
                name="Parse Web Page",
                description="Parse Web Page",
                type="langchain",
                model=ModelConfig(provider="ollama"),
                system_prompts=[
                    PromptConfig(
                        role="system",
                        content="You are an assistant that parses web pages."
                                "  Let’s think step by step and take your time to get the right answer."
                                "  Try the get_web_page tool first and if you don't get the answer then use the scraping_bee_web_scraper tool.",
                    )
                ],
                tools=[
                    AgentConfig(name="google_search"),
                    AgentConfig(name="get_web_page"),
                    AgentConfig(name="scraping_bee_web_scraper"),
                ],
            )
        ]
    )

    # init client and connect to localhost server
    client = AsyncOpenAI(
        api_key="fake-api-key",
        base_url="http://localhost:5000/api/v1",  # change the default port if needed
        http_client=async_client,
    )

    # call API
    chat_completion: ChatCompletion = await client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": "Get the doctor's address from https://www.medstarhealth.org/doctors/meggin-a-sabatino-dnp",
            }
        ],
        model="Parse Web Page",
    )

    print(chat_completion)
    # print the top "choice"
    content: Optional[str] = "\n".join(
        choice.message.content or "" for choice in chat_completion.choices
    )
    assert content is not None
    print(content)
    assert "3800 Reservoir" in content
