"""
Qwen tokenizer integration for accurate preflight token counting.

Loads the HuggingFace tokenizer for the configured backend model and counts tokens
by applying the model's chat template — capturing all formatting overhead (role
delimiters, BOS/EOS, tool-call markers, generation prompt) that the character-based
heuristic misses.

Tokenizer objects are cached after the first load so repeated requests are cheap.
"""

from __future__ import annotations

import functools
import logging
from typing import Any

from language_model_gateway.gateway.utilities.logger.log_levels import SRC_LOG_LEVELS

logger = logging.getLogger(__name__)
logger.setLevel(SRC_LOG_LEVELS.get("LLM", logging.INFO))

# Models that have permanently failed to load — skip future attempts.
_UNAVAILABLE: set[str] = set()


@functools.lru_cache(maxsize=8)
def _load_tokenizer(model_id: str) -> Any:
    """Load and cache a HuggingFace tokenizer. Logs on first use; cached forever."""
    from transformers import AutoTokenizer  # type: ignore[import-not-found]

    logger.info(
        "[coding-model-router] loading tokenizer '%s' (cached after first use)",
        model_id,
    )
    return AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)  # nosec B615


def count_oai_request_tokens(
    oai_body: dict[str, Any], tokenizer_model: str
) -> int | None:
    """
    Count tokens for an OpenAI-format request using the Qwen tokenizer.

    Applies the model's Jinja2 chat template so the count includes all overhead:
    system/user/assistant role tokens, tool-schema encoding, generation prompt, etc.

    Returns None if the tokenizer cannot be loaded (e.g. transformers not installed,
    model not cached). The caller should fall back gracefully in that case.
    """
    if tokenizer_model in _UNAVAILABLE:
        return None
    try:
        tok = _load_tokenizer(tokenizer_model)
        messages: list[dict[str, Any]] = oai_body.get("messages", [])
        tools: list[dict[str, Any]] | None = oai_body.get("tools") or None

        # apply_chat_template returns the raw string that will be tokenized by the model.
        # add_generation_prompt=True appends the "<|im_start|>assistant\n" prefix so we
        # include those tokens in our estimate.
        text: str = tok.apply_chat_template(
            messages,
            tools=tools,
            tokenize=False,
            add_generation_prompt=True,
        )
        return len(tok.encode(text))
    except ImportError:
        _UNAVAILABLE.add(tokenizer_model)
        logger.warning(
            "[coding-model-router] `transformers` not installed; "
            "tokenizer-based token counting unavailable for '%s'. "
            "Install it: uv add transformers",
            tokenizer_model,
        )
        return None
    except Exception as exc:
        _UNAVAILABLE.add(tokenizer_model)
        logger.warning(
            "[coding-model-router] failed to load tokenizer '%s': %s — "
            "falling back to character-based estimation",
            tokenizer_model,
            exc,
        )
        return None
