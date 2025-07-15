from pathlib import Path
from shutil import rmtree
from os import makedirs
import logging

import httpx
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion
from typing import List, Dict, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__file__)


def build_prompt(numbers: List[float]) -> str:
    if not numbers:
        return "Calculate the average of: "
    return f"Calculate the average of: {', '.join(map(str, numbers))}"


async def test_chat_calculator_average_tool_bedrock(
    async_client: httpx.AsyncClient,
) -> None:
    print("")
    data_dir = Path(__file__).parent.joinpath("./")
    temp_folder = data_dir.joinpath("../temp")
    if temp_folder.is_dir():
        rmtree(temp_folder)
    makedirs(temp_folder)

    test_cases: List[Dict[str, Any]] = [
        {"numbers": [10, 20, 30], "expected": "20.0"},
        {"numbers": [42], "expected": "42.0"},
        {"numbers": [], "expected": "No numbers provided"},
        {"numbers": [1.5, 2.5, 3.0], "expected": "2.333"},
        {"numbers": [-10, 0, 10], "expected": "0.0"},
    ]

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
