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
import json
import logging
from typing import Any

from language_model_gateway.gateway.utilities.logger.log_levels import SRC_LOG_LEVELS

logger = logging.getLogger(__name__)
logger.setLevel(SRC_LOG_LEVELS.get("LLM", logging.INFO))

# Models that have permanently failed to load — skip future attempts.
_UNAVAILABLE: set[str] = set()


def _flatten_message_content(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Normalize OpenAI-format message content to plain strings for apply_chat_template.

    The Qwen Jinja2 chat template expects content to be a string, but OpenAI-format
    messages may carry content as a list of typed blocks:
      [{"type": "text", "text": "..."}, {"type": "image_url", ...}]
    This function extracts text from each block and joins them so the tokenizer
    can process the message without a 'Can only get item pairs from a mapping' error.
    Tool-call and tool-result messages are also normalised.
    """
    result = []
    for msg in messages:
        msg = dict(msg)

        # Normalize list-typed content blocks to a plain string.
        content = msg.get("content")
        if isinstance(content, list):
            parts: list[str] = []
            for block in content:
                if isinstance(block, dict):
                    btype = block.get("type", "")
                    if btype == "text":
                        parts.append(block.get("text", ""))
                    elif btype in ("tool_result", "tool_use"):
                        inner = block.get("content") or block.get("output", "")
                        if isinstance(inner, list):
                            parts.extend(
                                b.get("text", "") for b in inner if isinstance(b, dict)
                            )
                        else:
                            parts.append(str(inner))
                    else:
                        # image_url, etc. — include a placeholder so token count isn't zero
                        parts.append(f"[{btype}]")
                else:
                    parts.append(str(block))
            msg["content"] = "\n".join(parts)

        # Normalize tool_calls: Qwen's Jinja2 template expects arguments as a dict,
        # but OpenAI format stores them as a JSON string.
        tool_calls = msg.get("tool_calls")
        if isinstance(tool_calls, list):
            fixed: list[dict[str, Any]] = []
            for tc in tool_calls:
                tc = dict(tc)
                fn = tc.get("function")
                if isinstance(fn, dict):
                    fn = dict(fn)
                    args = fn.get("arguments", "{}")
                    if isinstance(args, str):
                        try:
                            fn["arguments"] = json.loads(args)
                        except (json.JSONDecodeError, ValueError):
                            fn["arguments"] = {}
                    tc["function"] = fn
                fixed.append(tc)
            msg["tool_calls"] = fixed

        result.append(msg)
    return result


@functools.lru_cache(maxsize=8)
def _load_tokenizer(model_id: str) -> Any:
    """Load and cache a HuggingFace tokenizer. Logs on first use; cached forever."""
    from transformers import AutoTokenizer

    logger.info(
        "[coding-model-router] loading tokenizer '%s' (cached after first use)",
        model_id,
    )
    return AutoTokenizer.from_pretrained(model_id)


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

    # Flatten list-typed content blocks to strings; the Qwen Jinja2 chat template
    # requires string content and raises "Can only get item pairs from a mapping"
    # when it encounters OpenAI-format content block arrays.
    messages: list[dict[str, Any]] = _flatten_message_content(
        oai_body.get("messages", [])
    )
    tools: list[dict[str, Any]] | None = oai_body.get("tools") or None

    try:
        # apply_chat_template returns the raw string that will be tokenized by the model.
        # add_generation_prompt=True appends the "<|im_start|>assistant\n" prefix so we
        # include those tokens in our estimate.
        text: str = tok.apply_chat_template(
            messages,
            tools=tools,
            tokenize=False,
            add_generation_prompt=True,
        )
    except Exception as exc:
        if tools is not None:
            # The Qwen chat template may reject tools in certain formats. Retry without
            # tools — the count will be slightly lower but still accurate for message tokens.
            logger.warning(
                "[coding-model-router] apply_chat_template failed with tools for '%s': %s "
                "— retrying without tools argument",
                tokenizer_model,
                exc,
            )
            try:
                text = tok.apply_chat_template(
                    messages,
                    tokenize=False,
                    add_generation_prompt=True,
                )
            except Exception as exc2:
                logger.warning(
                    "[coding-model-router] apply_chat_template failed for '%s': %s "
                    "— falling back to character-based estimation for this request",
                    tokenizer_model,
                    exc2,
                )
                return None
        else:
            logger.warning(
                "[coding-model-router] apply_chat_template failed for '%s': %s "
                "— falling back to character-based estimation for this request",
                tokenizer_model,
                exc,
            )
            return None

    return len(tok.encode(text))
