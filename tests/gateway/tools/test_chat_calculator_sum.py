import logging

import httpx
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion
from typing import List, Dict, Any

from language_model_gateway.configs.config_schema import (
    ChatModelConfig,
    ModelConfig,
    AgentConfig,
)
from language_model_gateway.container.simple_container import SimpleContainer
from language_model_gateway.gateway.api_container import get_container_async
from language_model_gateway.gateway.utilities.expiring_cache import ExpiringCache

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__file__)


def build_prompt(numbers: List[float]) -> str:
    if not numbers:
        return "Calculate the sum of: "
    return f"Calculate the sum of: {', '.join(map(str, numbers))}"


async def test_chat_calculator_sum_tool_bedrock(
    async_client: httpx.AsyncClient,
) -> None:
    print("")
    print("")
    test_container: SimpleContainer = await get_container_async()

    # set the model configuration for this test
    model_configuration_cache: ExpiringCache[List[ChatModelConfig]] = (
        test_container.resolve(ExpiringCache)
    )

    await model_configuration_cache.set(
        [
            ChatModelConfig(
                id="general_purpose",
                name="General Purpose",
                description="General Purpose Language Model",
                type="langchain",
                model=ModelConfig(
                    provider="bedrock",
                    model="us.anthropic.claude-3-5-haiku-20241022-v1:0",
                ),
                tools=[
                    AgentConfig(name="calculator_sum"),
                ],
            )
        ]
    )

    test_cases: List[Dict[str, Any]] = [
        {"numbers": [10, 20, 30], "expected": "60.0"},
        {"numbers": [42], "expected": "42.0"},
        {"numbers": [], "expected": "No numbers provided"},
        {"numbers": [1.5, 2.5, 3.0], "expected": "7.0"},
        {"numbers": [-10, 0, 10], "expected": "0.0"},
    ]

    # init client and connect to localhost server
    client = AsyncOpenAI(
        api_key="fake-api-key",
        base_url="http://localhost:5000/api/v1",
        http_client=async_client,
    )

    # call API
    chat_completion: ChatCompletion = await client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": "what is the current date and time?",
            }
        ],
        model="General Purpose",
    )
    print(chat_completion)

    for idx, case in enumerate(test_cases):
        prompt: str = build_prompt(case["numbers"])
        print(f"\nSending prompt to Bedrock: {prompt}")

        # call API
        chat_completion = await client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            model="General Purpose",
        )

        print(chat_completion)
