import os

import pytest
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion, ChatCompletionUserMessageParam
from typing import Optional


@pytest.mark.skipif(
    os.environ.get("RUN_TESTS_WITH_REAL_LLM") != "1",
    reason="Environment Variable RUN_TESTS_WITH_REAL_LLM not set",
)
@pytest.mark.integration
async def test_aiden_api() -> None:
    """
    Placeholder for Aiden API integration test.
    :return: None
    """
    client = AsyncOpenAI(
        api_key="fake-api-key",  # pragma: allowlist secret
        # this api key is ignored for now.  suggest setting it to something that identifies your calling code
        base_url="https://language-model-gateway.services.bwell.zone/api/v1",
        default_headers={
            "Authorization": f"Bearer {os.getenv('AIDEN_OKTA_TOKEN')}",
        },
    )
    message: ChatCompletionUserMessageParam = {
        "role": "user",
        "content": "Use person id 4f77a49a-d8a8-4153-a2e9-13d6d0b4b301 for Imran Qureshi. Get my patient summary",  # specify your prompt here
    }
    chat_completion: ChatCompletion = await client.chat.completions.create(
        messages=[message],
        model="AI SDK Prod",
        # choose the task model - same as the task models in https://openwebui.services.bwell.zone/
    )
    content: Optional[str] = "\n".join(
        choice.message.content or "" for choice in chat_completion.choices
    )
    assert content is not None
    print("======= Response =======")
    print(content)
    print("======= End of Response =======")
