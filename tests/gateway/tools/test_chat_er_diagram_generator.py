from typing import Optional, List

import httpx
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion
from openai.types.chat.chat_completion import Choice

from language_model_gateway.configs.config_schema import (
    ChatModelConfig,
    ModelConfig,
    AgentConfig,
)
from language_model_gateway.container.simple_container import SimpleContainer
from language_model_gateway.gateway.api_container import get_container_async
from language_model_gateway.gateway.image_generation.image_generator_factory import (
    ImageGeneratorFactory,
)
from language_model_gateway.gateway.models.model_factory import ModelFactory
from language_model_gateway.gateway.utilities.environment_reader import (
    EnvironmentReader,
)
from language_model_gateway.gateway.utilities.expiring_cache import ExpiringCache
from tests.gateway.mocks.mock_chat_model import MockChatModel
from tests.gateway.mocks.mock_image_generator import MockImageGenerator
from tests.gateway.mocks.mock_image_generator_factory import MockImageGeneratorFactory
from tests.gateway.mocks.mock_model_factory import MockModelFactory


async def test_chat_er_diagram_generator(async_client: httpx.AsyncClient) -> None:
    print("")
    test_container: SimpleContainer = await get_container_async()

    if not EnvironmentReader.is_environment_variable_set("RUN_TESTS_WITH_REAL_LLM"):
        test_container.register(
            ModelFactory,
            lambda c: MockModelFactory(
                fn_get_model=lambda chat_model_config: MockChatModel(
                    fn_get_response=lambda messages: "http://localhost:5050/image_generation/"
                )
            ),
        )
        test_container.register(
            ImageGeneratorFactory,
            lambda c: MockImageGeneratorFactory(image_generator=MockImageGenerator()),
        )

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
                    AgentConfig(name="er_diagram_generator"),
                ],
            )
        ]
    )

    # Test health endpoint
    # response = await async_client.get("/health")
    # assert response.status_code == 200

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
                "content": """
Generate an Entity-Relationship Diagram with the following specifications:

Entities and Attributes:
1. User Entity
   - user_id* (primary key)
   - username
   - email
   - registration_date

2. Product Entity
   - product_id* (primary key)
   - name
   - price
   - category
   - stock_quantity

3. Order Entity
   - order_id* (primary key)
   - user_id (foreign key)
   - order_date
   - total_amount
   - status

Relationships:
- User places Order (one_to_many)
- Order contains Product (many_to_many)
- Product belongs to Category (many_to_one)

Diagram Requirements:
- Use distinct colors for each entity
- Clearly mark primary keys
- Show relationship cardinalities
""",
            }
        ],
        model="General Purpose",
    )

    print(chat_completion)

    # print the top "choice"
    choices: List[Choice] = chat_completion.choices
    print(choices)
    content: Optional[str] = ",".join(
        [choice.message.content or "" for choice in choices]
    )
    assert content is not None
    print(content)
    assert "http://localhost:5050/image_generation/" in content
    # assert "data:image/png;base64" in content
