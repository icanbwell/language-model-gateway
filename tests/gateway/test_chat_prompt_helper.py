from typing import Optional

import httpx
from openai import AsyncOpenAI, AsyncStream
from openai.types.chat import ChatCompletion, ChatCompletionChunk

from language_model_gateway.configs.config_schema import (
    ChatModelConfig,
    ModelConfig,
    PromptConfig,
    ModelParameterConfig,
)
from language_model_gateway.gateway.utilities.cache.config_expiring_cache import (
    ConfigExpiringCache,
)
from oidcauthlib.container.simple_container import SimpleContainer
from language_model_gateway.gateway.api_container import get_container_async
from language_model_gateway.gateway.models.model_factory import ModelFactory
from language_model_gateway.gateway.utilities.environment_reader import (
    EnvironmentReader,
)
from tests.gateway.mocks.mock_chat_model import MockChatModel
from tests.gateway.mocks.mock_model_factory import MockModelFactory


async def test_chat_prompt_helper(async_client: httpx.AsyncClient) -> None:
    print("")

    test_container: SimpleContainer = await get_container_async()

    if not EnvironmentReader.is_environment_variable_set("RUN_TESTS_WITH_REAL_LLM"):
        test_container.register(
            ModelFactory,
            lambda c: MockModelFactory(
                fn_get_model=lambda chat_model_config: MockChatModel(
                    fn_get_response=lambda messages: "doctor"
                )
            ),
        )

    model_configuration_cache: ConfigExpiringCache = test_container.resolve(
        ConfigExpiringCache
    )
    await model_configuration_cache.set(
        [
            ChatModelConfig(
                id="prompt_helper",
                name="Prompt Helper",
                description="Prompt Helper",
                type="langchain",
                model=ModelConfig(
                    provider="bedrock",
                    model="us.anthropic.claude-3-5-haiku-20241022-v1:0",
                ),
                model_parameters=[ModelParameterConfig(key="temperature", value=0.5)],
                system_prompts=[
                    PromptConfig(
                        role="system",
                        content='Given a task description or existing prompt, produce a detailed system prompt to guide a language model in completing the task effectively.\n\n# Guidelines\n\n- Understand the Task: Grasp the main objective, goals, requirements, constraints, and expected output.\n- Minimal Changes: If an existing prompt is provided, improve it only if it\'s simple. For complex prompts, enhance clarity and add missing elements without altering the original structure.\n- Reasoning Before Conclusions**: Encourage reasoning steps before any conclusions are reached. ATTENTION! If the user provides examples where the reasoning happens afterward, REVERSE the order! NEVER START EXAMPLES WITH CONCLUSIONS!\n    - Reasoning Order: Call out reasoning portions of the prompt and conclusion parts (specific fields by name). For each, determine the ORDER in which this is done, and whether it needs to be reversed.\n    - Conclusion, classifications, or results should ALWAYS appear last.\n- Examples: Include high-quality examples if helpful, using placeholders [in brackets] for complex elements.\n   - What kinds of examples may need to be included, how many, and whether they are complex enough to benefit from placeholders.\n- Clarity and Conciseness: Use clear, specific language. Avoid unnecessary instructions or bland statements.\n- Formatting: Use markdown features for readability. DO NOT USE ``` CODE BLOCKS UNLESS SPECIFICALLY REQUESTED.\n- Preserve User Content: If the input task or prompt includes extensive guidelines or examples, preserve them entirely, or as closely as possible. If they are vague, consider breaking down into sub-steps. Keep any details, guidelines, examples, variables, or placeholders provided by the user.\n- Constants: DO include constants in the prompt, as they are not susceptible to prompt injection. Such as guides, rubrics, and examples.\n- Output Format: Explicitly the most appropriate output format, in detail. This should include length and syntax (e.g. short sentence, paragraph, JSON, etc.)\n    - For tasks outputting well-defined or structured data (classification, JSON, etc.) bias toward outputting a JSON.\n    - JSON should never be wrapped in code blocks (```) unless explicitly requested.\n\nThe final prompt you output should adhere to the following structure below. Do not include any additional commentary, only output the completed system prompt. SPECIFICALLY, do not include any additional messages at the start or end of the prompt. (e.g. no "---")\n\n[Concise instruction describing the task - this should be the first line in the prompt, no section header]\n\n[Additional details as needed.]\n\n[Optional sections with headings or bullet points for detailed steps.]\n\n# Steps [optional]\n\n[optional: a detailed breakdown of the steps necessary to accomplish the task]\n\n# Output Format\n\n[Specifically call out how the output should be formatted, be it response length, structure e.g. JSON, markdown, etc]\n\n# Examples [optional]\n\n[Optional: 1-3 well-defined examples with placeholders if necessary. Clearly mark where examples start and end, and what the input and output are. User placeholders as necessary.]\n[If the examples are shorter than what a realistic example is expected to be, make a reference with () explaining how real examples should be longer / shorter / different. AND USE PLACEHOLDERS! ]\n\n# Notes [optional]\n\n[optional: edge cases, details, and an area to call or repeat out specific important considerations]',
                    ),
                    PromptConfig(
                        role="system",
                        content="The user will provide a Task, Goal, or Current Prompt.",
                    ),
                ],
                # tools=[
                #     ToolConfig(
                #         name="current_date"
                #     )
                # ]
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
                "content": "I want to find doctors in the country that are part of John Muir Health and work in Walnut Creek. And are family doctors",
            }
        ],
        model="Prompt Helper",
    )

    # print the top "choice"
    content: Optional[str] = "\n".join(
        choice.message.content or "" for choice in chat_completion.choices
    )

    assert content is not None
    print(content)
    assert "doctor" in content


async def test_chat_prompt_helper_streaming(async_client: httpx.AsyncClient) -> None:
    print("")

    test_container: SimpleContainer = await get_container_async()

    if not EnvironmentReader.is_environment_variable_set("RUN_TESTS_WITH_REAL_LLM"):
        test_container.register(
            ModelFactory,
            lambda c: MockModelFactory(
                fn_get_model=lambda chat_model_config: MockChatModel(
                    fn_get_response=lambda messages: "doctor"
                )
            ),
        )

    model_configuration_cache: ConfigExpiringCache = test_container.resolve(
        ConfigExpiringCache
    )
    await model_configuration_cache.set(
        [
            ChatModelConfig(
                id="prompt_helper",
                name="Prompt Helper",
                description="Prompt Helper",
                type="langchain",
                model=ModelConfig(
                    provider="bedrock",
                    model="us.anthropic.claude-3-5-haiku-20241022-v1:0",
                ),
                model_parameters=[ModelParameterConfig(key="temperature", value=0.5)],
                system_prompts=[
                    PromptConfig(
                        role="system",
                        content='Given a task description or existing prompt, produce a detailed system prompt to guide a language model in completing the task effectively.\n\n# Guidelines\n\n- Understand the Task: Grasp the main objective, goals, requirements, constraints, and expected output.\n- Minimal Changes: If an existing prompt is provided, improve it only if it\'s simple. For complex prompts, enhance clarity and add missing elements without altering the original structure.\n- Reasoning Before Conclusions**: Encourage reasoning steps before any conclusions are reached. ATTENTION! If the user provides examples where the reasoning happens afterward, REVERSE the order! NEVER START EXAMPLES WITH CONCLUSIONS!\n    - Reasoning Order: Call out reasoning portions of the prompt and conclusion parts (specific fields by name). For each, determine the ORDER in which this is done, and whether it needs to be reversed.\n    - Conclusion, classifications, or results should ALWAYS appear last.\n- Examples: Include high-quality examples if helpful, using placeholders [in brackets] for complex elements.\n   - What kinds of examples may need to be included, how many, and whether they are complex enough to benefit from placeholders.\n- Clarity and Conciseness: Use clear, specific language. Avoid unnecessary instructions or bland statements.\n- Formatting: Use markdown features for readability. DO NOT USE ``` CODE BLOCKS UNLESS SPECIFICALLY REQUESTED.\n- Preserve User Content: If the input task or prompt includes extensive guidelines or examples, preserve them entirely, or as closely as possible. If they are vague, consider breaking down into sub-steps. Keep any details, guidelines, examples, variables, or placeholders provided by the user.\n- Constants: DO include constants in the prompt, as they are not susceptible to prompt injection. Such as guides, rubrics, and examples.\n- Output Format: Explicitly the most appropriate output format, in detail. This should include length and syntax (e.g. short sentence, paragraph, JSON, etc.)\n    - For tasks outputting well-defined or structured data (classification, JSON, etc.) bias toward outputting a JSON.\n    - JSON should never be wrapped in code blocks (```) unless explicitly requested.\n\nThe final prompt you output should adhere to the following structure below. Do not include any additional commentary, only output the completed system prompt. SPECIFICALLY, do not include any additional messages at the start or end of the prompt. (e.g. no "---")\n\n[Concise instruction describing the task - this should be the first line in the prompt, no section header]\n\n[Additional details as needed.]\n\n[Optional sections with headings or bullet points for detailed steps.]\n\n# Steps [optional]\n\n[optional: a detailed breakdown of the steps necessary to accomplish the task]\n\n# Output Format\n\n[Specifically call out how the output should be formatted, be it response length, structure e.g. JSON, markdown, etc]\n\n# Examples [optional]\n\n[Optional: 1-3 well-defined examples with placeholders if necessary. Clearly mark where examples start and end, and what the input and output are. User placeholders as necessary.]\n[If the examples are shorter than what a realistic example is expected to be, make a reference with () explaining how real examples should be longer / shorter / different. AND USE PLACEHOLDERS! ]\n\n# Notes [optional]\n\n[optional: edge cases, details, and an area to call or repeat out specific important considerations]',
                    ),
                    PromptConfig(
                        role="system",
                        content="The user will provide a Task, Goal, or Current Prompt.",
                    ),
                ],
                # tools=[
                #     ToolConfig(
                #         name="current_date"
                #     )
                # ]
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
    stream: AsyncStream[ChatCompletionChunk] = await client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": "I want to find doctors in the country that are part of John Muir Health and work in Walnut Creek. And are family doctors",
            }
        ],
        model="Prompt Helper",
        stream=True,
    )

    # print the top "choice"
    content: str = ""
    async for chunk in stream:
        delta_content = "\n".join(
            [choice.delta.content or "" for choice in chunk.choices]
        )
        content += delta_content
        print("------ CHUNK ------")
        print(delta_content)
        print("------ END CHUNK ------")

    assert content is not None
    print("------ FINAL CONTENT ------")
    print(content)
    print("------ END FINAL CONTENT ------")
    assert "doctor" in content
