"""
Throwaway spike script for BAI-306: determine whether Bedrock Mantle offers
any prompt-caching benefit for the haiku/sonnet (Qwen) tiers. See
docs/superpowers/specs/2026-07-13-bedrock-mantle-prompt-caching-design.md.

Usage:
    AWS_PROFILE=cloud-lead-dev uv run python scripts/prompt_caching_spike.py
"""

from __future__ import annotations

import time
import uuid
from typing import Any

import httpx
import openai

from language_model_gateway.gateway.routers.model_routing.aws_auth import SigV4Auth

AWS_REGION = "us-east-1"
BASE_URL = "https://bedrock-mantle.us-east-1.api.aws/v1"
MODELS = ["qwen.qwen3-coder-30b-a3b-v1:0", "qwen.qwen3-coder-next"]

RUN_ID = uuid.uuid4().hex[:8]

# Representative of a real Claude Code system prompt + tool defs, long enough
# to clear the ~1024-token minimum OpenAI's own automatic caching requires.
LONG_PREFIX_BASE = "You are a coding assistant working in a large repository. " * 200


def _client(route: dict[str, Any]) -> openai.OpenAI:
    http_client = httpx.Client(auth=SigV4Auth(route), timeout=30.0)
    return openai.OpenAI(
        api_key="dummy",  # pragma: allowlist secret
        base_url=BASE_URL,
        http_client=http_client,
        max_retries=0,
    )


def check_chat_completions_caching(model: str) -> None:
    """Question 1: does repeating an identical long prefix reduce
    cached_tokens=0 on a second call, with and without explicit
    prompt_cache_key/prompt_cache_retention hints?"""
    route: dict[str, Any] = {"aws_region": AWS_REGION}
    client = _client(route)
    variants: list[dict[str, Any]] = [
        {"label": "no cache params"},
        {
            "label": "prompt_cache_key set",
            "prompt_cache_key": f"bai-306-spike-key-{RUN_ID}",
        },
        {
            "label": "prompt_cache_retention=24h",
            "prompt_cache_key": f"bai-306-spike-key-24h-{RUN_ID}",
            "prompt_cache_retention": "24h",
        },
    ]
    for variant_index, variant in enumerate(variants):
        label = variant.pop("label")
        variant_prefix = f"[run:{RUN_ID}] [variant:{variant_index}] " + LONG_PREFIX_BASE
        for call_index in range(2):
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": variant_prefix},
                    {"role": "user", "content": f"Say hello, attempt {call_index}"},
                ],
                **variant,
            )
            usage = resp.usage
            details = usage.prompt_tokens_details if usage else None
            cached = details.cached_tokens if details else None
            print(
                f"[{model}] variant={label!r} call={call_index} "
                f"prompt_tokens={usage.prompt_tokens if usage else None} "
                f"cached_tokens={cached}"
            )
            time.sleep(1)


def main() -> None:
    for model in MODELS:
        check_chat_completions_caching(model)


if __name__ == "__main__":
    main()
