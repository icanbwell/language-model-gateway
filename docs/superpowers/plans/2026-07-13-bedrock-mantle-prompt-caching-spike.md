# Bedrock Mantle Prompt-Caching Spike Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Empirically determine, against the real `bedrock-mantle.us-east-1.api.aws` endpoint, whether any prompt-caching benefit exists today for the `haiku`/`sonnet` tiers (Qwen models) — via passive automatic caching, the OpenAI SDK's explicit `prompt_cache_key`/`prompt_cache_retention` fields on Chat Completions, or the Responses API's `previous_response_id` statefulness — and record the findings in the design spec so the next phase (implementation, or closing the initiative out) is a data-driven decision rather than a guess.

**Architecture:** A single throwaway script (`scripts/prompt_caching_spike.py`) reuses the router's existing `SigV4Auth` (from `aws_auth.py`) to authenticate against Bedrock Mantle exactly as `router.py` does in production, then runs three checks against the real API using the OpenAI SDK. It is committed temporarily (so pre-commit/CI-equivalent checks apply and the exact commands are reviewable) and deleted in the final task once its findings are captured in the spec — it is not part of the shipped application.

**Tech Stack:** Python 3.12, `openai>=2.5.0` SDK (already a project dependency; `client.chat.completions.create` and `client.responses.create` used directly), `httpx` for the SigV4-signed transport, `boto3`/AWS SSO credentials via `AWS_PROFILE`.

## Global Constraints

- Requires valid AWS credentials for Bedrock Mantle. In this environment: `aws sso login --profile cloud-lead-dev` (the profile found configured here had an expired SSO token as of this writing).
- Target endpoint: `https://bedrock-mantle.us-east-1.api.aws/v1` (`aws_region="us-east-1"`), matching `model-router-config.json`.
- Target models: `qwen.qwen3-coder-30b-a3b-v1:0` (haiku tier) and `qwen.qwen3-coder-next` (sonnet tier) — the exact two models already routed to in production.
- This script is exploratory and hits a live external API — there are no pytest unit tests for it. Each task's "test cycle" is: run the script against the real endpoint and read the printed output, per the exact commands given in that task.
- The script must still pass this repo's pre-commit hooks (ruff, ruff format, mypy `--strict`, bandit) while it exists in the repo, same as any other Python file — `docs/` is excluded from those hooks, `scripts/` is not.
- Findings go into `docs/superpowers/specs/2026-07-13-bedrock-mantle-prompt-caching-design.md` (append a dated "## Phase 0 findings" section) — do not create a second findings document.
- Commit messages must start with `BAI-306` per this repo's convention (no `feat:`/`fix:` prefixes).

---

### Task 1: Script scaffold + Chat Completions caching check (Question 1)

**Files:**
- Create: `scripts/prompt_caching_spike.py`
- Test: manual run against live Bedrock Mantle (see Step 3/4 below — no automated test file)

**Interfaces:**
- Produces: `_client(route: dict[str, Any]) -> openai.OpenAI` (module-level helper, reused by Tasks 2 and 3)
- Produces: `check_chat_completions_caching(model: str) -> None` (module-level function, reused by `main()` added in this task)

- [ ] **Step 1: Confirm AWS credentials are live**

Run: `AWS_PROFILE=cloud-lead-dev aws sts get-caller-identity`
Expected: JSON output with an `Account`/`Arn` field, not an SSO token error. If it errors, run `aws sso login --profile cloud-lead-dev` first and retry.

- [ ] **Step 2: Write the script scaffold and the Chat Completions check**

Create `scripts/prompt_caching_spike.py`:

```python
"""
Throwaway spike script for BAI-306: determine whether Bedrock Mantle offers
any prompt-caching benefit for the haiku/sonnet (Qwen) tiers. See
docs/superpowers/specs/2026-07-13-bedrock-mantle-prompt-caching-design.md.

Usage:
    AWS_PROFILE=cloud-lead-dev uv run python scripts/prompt_caching_spike.py
"""

from __future__ import annotations

import time
from typing import Any

import httpx
import openai

from language_model_gateway.gateway.routers.model_routing.aws_auth import SigV4Auth

AWS_REGION = "us-east-1"
BASE_URL = "https://bedrock-mantle.us-east-1.api.aws/v1"
MODELS = ["qwen.qwen3-coder-30b-a3b-v1:0", "qwen.qwen3-coder-next"]

# Representative of a real Claude Code system prompt + tool defs, long enough
# to clear the ~1024-token minimum OpenAI's own automatic caching requires.
LONG_PREFIX = "You are a coding assistant working in a large repository. " * 200


def _client(route: dict[str, Any]) -> openai.OpenAI:
    http_client = httpx.Client(auth=SigV4Auth(route), timeout=30.0)
    return openai.OpenAI(
        api_key="dummy",
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
        {"label": "prompt_cache_key set", "prompt_cache_key": "bai-306-spike-key"},
        {
            "label": "prompt_cache_retention=24h",
            "prompt_cache_key": "bai-306-spike-key-24h",
            "prompt_cache_retention": "24h",
        },
    ]
    for variant in variants:
        label = variant.pop("label")
        for call_index in range(2):
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": LONG_PREFIX},
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
```

- [ ] **Step 3: Run the script for real and record raw output**

Run: `AWS_PROFILE=cloud-lead-dev uv run python scripts/prompt_caching_spike.py`
Expected: 2 models × 3 variants × 2 calls = 12 printed lines, each with a `cached_tokens` value (`None` or an integer). Save this raw output — Task 4 needs it verbatim for the spec's findings section. If any call raises an exception instead of printing, capture the exception text too; a model/variant combination erroring is itself a finding (e.g. `prompt_cache_retention` might be rejected outright).

- [ ] **Step 4: Commit**

```bash
git add scripts/prompt_caching_spike.py
git commit -m "BAI-306 Add Bedrock Mantle Chat Completions caching spike script"
```

This repo's pre-commit hook runs ruff, ruff format, mypy `--strict`, and bandit automatically on `git commit` (see `.pre-commit-config.yaml`) — expect it to build a Docker image the first time (a minute or two) and then run each check inline. Expected: all hooks pass and the commit succeeds. If mypy or ruff fails, fix the reported line in `scripts/prompt_caching_spike.py` and re-run `git commit` with the same message (pre-existing errors in unrelated files, like missing `structlog`/`transformers` stubs, are not this task's concern).

---

### Task 2: Responses API model-compatibility check (Question 2)

**Files:**
- Modify: `scripts/prompt_caching_spike.py`

**Interfaces:**
- Consumes: `_client(route: dict[str, Any]) -> openai.OpenAI` (from Task 1)
- Produces: `check_responses_api_support(model: str) -> bool` (module-level function; `True` return feeds Task 3)

- [ ] **Step 1: Add the compatibility check function**

Add to `scripts/prompt_caching_spike.py`, above `def main() -> None:`:

```python
def check_responses_api_support(model: str) -> bool:
    """Question 2: does this model accept a Responses API call at all?"""
    route: dict[str, Any] = {"aws_region": AWS_REGION}
    client = _client(route)
    try:
        resp = client.responses.create(
            model=model,
            input=[{"role": "user", "content": "Hello"}],
        )
        print(f"[{model}] Responses API: SUPPORTED (response id={resp.id})")
        return True
    except Exception as exc:  # noqa: BLE001 - any failure means "not supported"
        print(f"[{model}] Responses API: NOT SUPPORTED ({type(exc).__name__}: {exc})")
        return False
```

- [ ] **Step 2: Wire it into `main()`**

Replace the existing `main()` function with:

```python
def main() -> None:
    for model in MODELS:
        check_chat_completions_caching(model)
    for model in MODELS:
        check_responses_api_support(model)


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Run the script for real**

Run: `AWS_PROFILE=cloud-lead-dev uv run python scripts/prompt_caching_spike.py`
Expected: the Task 1 output, plus one `SUPPORTED`/`NOT SUPPORTED` line per model. Record which models return `SUPPORTED` — this determines whether Task 3 runs for that model.

- [ ] **Step 4: Commit**

```bash
git add scripts/prompt_caching_spike.py
git commit -m "BAI-306 Add Responses API model-compatibility check to caching spike"
```

The pre-commit hook runs ruff/mypy/bandit automatically. Expected: all hooks pass. Bandit may flag the bare `except Exception` in `check_responses_api_support` — if so, add `# nosec B110` on that line with a short comment explaining the broad catch is intentional (any exception means "not supported"), then re-run `git commit` with the same message.

---

### Task 3: Responses API statefulness benefit check (Question 3)

**Only runs for models where Task 2 printed `SUPPORTED`.** If neither model supports the Responses API, skip this task entirely, note that in the findings (Task 4), and do not add this code — an untestable function is dead code, not a deliverable.

**Files:**
- Modify: `scripts/prompt_caching_spike.py`

**Interfaces:**
- Consumes: `_client(route: dict[str, Any]) -> openai.OpenAI` (from Task 1), `check_responses_api_support(model: str) -> bool` (from Task 2)
- Produces: `check_previous_response_id_benefit(model: str) -> None` (module-level function)

- [ ] **Step 1: Add the statefulness benefit check**

Add to `scripts/prompt_caching_spike.py`, above `def main() -> None:`:

```python
def check_previous_response_id_benefit(model: str) -> None:
    """Question 3: does previous_response_id skip recomputation (latency/
    token benefit), or just avoid resending bytes over the wire?"""
    route: dict[str, Any] = {"aws_region": AWS_REGION}
    client = _client(route)

    start = time.perf_counter()
    first = client.responses.create(
        model=model,
        input=[
            {"role": "system", "content": LONG_PREFIX},
            {"role": "user", "content": "What is 2+2?"},
        ],
    )
    cold_latency = time.perf_counter() - start
    print(f"[{model}] cold call: latency={cold_latency:.2f}s usage={first.usage}")

    start = time.perf_counter()
    follow_up = client.responses.create(
        model=model,
        previous_response_id=first.id,
        input=[{"role": "user", "content": "And what is 3+3?"}],
    )
    stateful_latency = time.perf_counter() - start
    print(
        f"[{model}] stateful follow-up: latency={stateful_latency:.2f}s "
        f"usage={follow_up.usage}"
    )

    start = time.perf_counter()
    manual = client.responses.create(
        model=model,
        input=[
            {"role": "system", "content": LONG_PREFIX},
            {"role": "user", "content": "What is 2+2?"},
            {"role": "assistant", "content": first.output_text},
            {"role": "user", "content": "And what is 3+3?"},
        ],
    )
    manual_latency = time.perf_counter() - start
    print(
        f"[{model}] manual full-history call: latency={manual_latency:.2f}s "
        f"usage={manual.usage}"
    )
```

- [ ] **Step 2: Wire it into `main()`, conditional on support**

Replace `main()` with:

```python
def main() -> None:
    for model in MODELS:
        check_chat_completions_caching(model)
    for model in MODELS:
        if check_responses_api_support(model):
            check_previous_response_id_benefit(model)


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Run the script for real**

Run: `AWS_PROFILE=cloud-lead-dev uv run python scripts/prompt_caching_spike.py`
Expected: if either model supported the Responses API in Task 2, three additional lines per that model (cold call, stateful follow-up, manual full-history call), each with a `usage=` object. Compare `input_tokens`/`input_tokens_details.cached_tokens` and latency across the three lines — that comparison is the actual answer to Question 3.

- [ ] **Step 4: Commit** (skip if this task was skipped entirely per the note above)

```bash
git add scripts/prompt_caching_spike.py
git commit -m "BAI-306 Add previous_response_id statefulness benefit check to caching spike"
```

The pre-commit hook runs ruff/mypy/bandit automatically. Expected: all hooks pass.

---

### Task 4: Record findings in the spec, remove the spike script

**Files:**
- Modify: `docs/superpowers/specs/2026-07-13-bedrock-mantle-prompt-caching-design.md`
- Delete: `scripts/prompt_caching_spike.py`

**Interfaces:**
- Consumes: raw output captured in Tasks 1 Step 4, 2 Step 4, and 3 Step 4

- [ ] **Step 1: Append the findings section to the spec**

Add this section to the end of `docs/superpowers/specs/2026-07-13-bedrock-mantle-prompt-caching-design.md`, filling in the bracketed placeholders with the actual captured output — this step cannot be completed until Tasks 1-3 have produced real output, since the values are not knowable in advance:

```markdown
## Phase 0 findings (2026-07-13)

**Question 1 — Chat Completions caching signal:**
[paste the 12 lines of output from Task 1 Step 3, or a summary table:
 model | variant | call 0 cached_tokens | call 1 cached_tokens]

**Question 2 — Responses API model compatibility:**
[SUPPORTED/NOT SUPPORTED per model, from Task 2 Step 3]

**Question 3 — previous_response_id statefulness benefit:**
[latency + usage comparison across cold/stateful/manual calls, from Task 3
 Step 3, or "Not applicable — neither model supports the Responses API."]

**Conclusion:** [Path A / Path B / Path C, per the decision branches above,
with a one-sentence justification citing the numbers above.]
```

- [ ] **Step 2: Delete the spike script**

Run: `git rm scripts/prompt_caching_spike.py`

- [ ] **Step 3: Commit**

```bash
git add docs/superpowers/specs/2026-07-13-bedrock-mantle-prompt-caching-design.md
git commit -m "BAI-306 Record Phase 0 spike findings, remove throwaway spike script"
```

- [ ] **Step 4: Push and report the conclusion**

Run: `git push`
Report back which Path (A, B, or C) the findings point to — that decision determines the next plan (Path A: a short follow-up plan for the determinism audit + observability; Path B: a new brainstorming/spec cycle for the Responses API migration, not a direct implementation plan; Path C: close out, no further plan needed).
