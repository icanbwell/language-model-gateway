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
from language_model_gateway.gateway.utilities.cache.config_expiring_cache import (
    ConfigExpiringCache,
)
from language_model_gateway.gateway.image_generation.image_generator_factory import (
    ImageGeneratorFactory,
)
from language_model_gateway.gateway.models.model_factory import ModelFactory
from language_model_gateway.gateway.utilities.environment_reader import (
    EnvironmentReader,
)
from tests.gateway.mocks.mock_chat_model import MockChatModel
from tests.gateway.mocks.mock_image_generator import MockImageGenerator
from tests.gateway.mocks.mock_image_generator_factory import MockImageGeneratorFactory
from tests.gateway.mocks.mock_model_factory import MockModelFactory
from oidcauthlib.container.interfaces import IContainer
from tests.common import get_test_container


async def test_chat_network_topology_diagram_generator(
    async_client: httpx.AsyncClient,
) -> None:
    print("")
    test_container: IContainer = get_test_container()

    if not EnvironmentReader.is_environment_variable_set("RUN_TESTS_WITH_REAL_LLM"):
        test_container.singleton(
            ModelFactory,
            lambda c: MockModelFactory(
                fn_get_model=lambda chat_model_config: MockChatModel(
                    fn_get_response=lambda messages: "http://localhost:5050/image_generation/"
                )
            ),
        )
        test_container.singleton(
            ImageGeneratorFactory,
            lambda c: MockImageGeneratorFactory(image_generator=MockImageGenerator()),
        )

    # set the model configuration for this test
    model_configuration_cache: ConfigExpiringCache = test_container.resolve(
        ConfigExpiringCache
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
                    AgentConfig(name="network_topology_generator"),
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
Create a network topology diagram with the following specifications:

Instructions:
- Specify nodes (network components) with their types
- Define connections between nodes
- Optional: Add labels to connections
- Optional: Customize node styles

Node Types:
- cloud: Represents internet or external network
- router: Network routing device
- switch: Network switch
- server: Server or computer
- firewall: Security device

Styling Options:
- shape: cloud, router, switch, server, firewall
- color: lightblue, lightgreen, lightgray, lightcoral, etc.

Example Format:
```json
{
    "nodes": {
        "Internet": {"style": {"shape": "cloud", "color": "lightgray"}},
        "Firewall": {"style": {"shape": "firewall", "color": "lightcoral"}},
        "Router": {"style": {"shape": "router", "color": "lightblue"}},
        "Switch1": {"style": {"shape": "switch", "color": "lightgreen"}},
        "Server1": {"style": {"shape": "server", "color": "lightpink"}}
    },
    "connections": [
        {"from": "Internet", "to": "Firewall", "label": "WAN"},
        {"from": "Firewall", "to": "Router", "label": "Secured"},
        {"from": "Router", "to": "Switch1", "label": "LAN"},
        {"from": "Switch1", "to": "Server1", "label": "eth0"}
    ],
    "title": "Simple Corporate Network"
}
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


async def test_chat_network_topology_diagram_generator_markdown(
    async_client: httpx.AsyncClient,
) -> None:
    print("")
    test_container: IContainer = get_test_container()

    if not EnvironmentReader.is_environment_variable_set("RUN_TESTS_WITH_REAL_LLM"):
        test_container.singleton(
            ModelFactory,
            lambda c: MockModelFactory(
                fn_get_model=lambda chat_model_config: MockChatModel(
                    fn_get_response=lambda messages: "http://localhost:5050/image_generation/"
                )
            ),
        )
        test_container.singleton(
            ImageGeneratorFactory,
            lambda c: MockImageGeneratorFactory(image_generator=MockImageGenerator()),
        )

    # set the model configuration for this test
    model_configuration_cache: ConfigExpiringCache = test_container.resolve(
        ConfigExpiringCache
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
                    AgentConfig(name="network_topology_generator"),
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
# Home Network Topology Diagram

## Network Components
- **Internet Modem**: Cloud, gray
- **Wireless Router**: Router, blue
- **Laptop 1**: Server, green
- **Laptop 2**: Server, green
- **Desktop**: Server, blue
- **Network Printer**: Server, yellow

## Connections
- Internet Modem → Wireless Router: "Internet"
- Wireless Router → Laptop 1: "WiFi"
- Wireless Router → Laptop 2: "WiFi"
- Wireless Router → Desktop: "Ethernet"
- Wireless Router → Network Printer: "Print Server"

## Diagram Title
Home Network Infrastructure
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
