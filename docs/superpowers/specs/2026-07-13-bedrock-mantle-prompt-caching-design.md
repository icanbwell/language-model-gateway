# Prompt caching for the haiku/sonnet (Bedrock Mantle / Qwen) tiers

## Problem

Claude Code sends Anthropic Messages API requests with explicit `cache_control`
breakpoints (system prompt, tool definitions, shared conversation prefix) so Anthropic's
own infrastructure can skip reprocessing repeated context — cheaper and faster on long
agentic sessions. `CodingModelRouter` forwards this untouched today only for the
`opus`/`fable` tiers, which pass through verbatim to `https://api.anthropic.com/v1/messages`
(`auth: passthrough`). Real Anthropic-side caching already applies there, unrelated to
anything in this document.

`haiku`/`sonnet` route instead to Qwen models via
`https://bedrock-mantle.us-east-1.api.aws/v1/chat/completions` (`auth: aws`,
`api_type: openai`) — these are the cost-sensitive tiers
(`price_per_mtok` 0.15 / 0.5 vs. 5.0 / 10.0 for opus/fable) with a 262k context window, so
they're exactly where repeated-prefix caching would matter most for both cost and latency.
`_anthropic_to_openai_request` (`message_translator.py`) drops `cache_control` entirely
when translating to Chat Completions format — there is no equivalent field to translate it
into. AWS's own `bedrock-mantle.html` documentation (verified by fetching it directly) makes
no mention of caching, `cache_control`, cached-token counts, or any caching mechanism for
either the Chat Completions or Responses surface of this endpoint. Whether Bedrock Mantle
does *any* automatic caching under the hood, and whether the Responses API's stateful
conversation management (`previous_response_id`) provides a real compute/latency benefit
rather than just a payload-size convenience, are both genuinely unconfirmed — undocumented
either way.

## Goal

Determine whether any caching benefit is achievable for `haiku`/`sonnet` traffic, and if
so, implement it — measured by cost (billed input tokens) and/or latency
(time-to-first-token on long contexts), weighted equally.

## Non-goals

- `opus`/`fable` — already correct via verbatim passthrough; not touched by this work.
- Any change to the Anthropic-format passthrough path (`_send_with_bedrock_retry`,
  `_stream_passthrough*`) in `bedrock_client.py`/`stream_converter.py`.
- Building a gateway-side response cache as a substitute for real prompt caching. It
  wouldn't help the actual problem (repeated-prefix-in-growing-conversation cost/latency):
  each turn's full request still differs from the last by the new trailing message even
  when the shared prefix is byte-identical, so a cache keyed on exact request match would
  almost never hit in a real multi-turn session.

## Phase 0 — empirical spike (blocking; must run before any implementation)

A standalone script, run against the real `bedrock-mantle.us-east-1.api.aws` endpoint using
the same models/auth this router already uses (`qwen.qwen3-coder-30b-a3b-v1:0`,
`qwen.qwen3-coder-next`, SigV4 via `AWS_PROFILE`), answering three questions. This cannot be
simulated with `httpx_mock` — it's testing real upstream behavior, not our own code.

**Prerequisite:** valid AWS credentials for Bedrock Mantle access. In this environment,
that's the `cloud-lead-dev` profile (`AWS_PROFILE=cloud-lead-dev`), whose SSO token had
expired as of this writing — run `aws sso login --profile cloud-lead-dev` first.

1. **Chat Completions caching signal.** Send an identical long prefix (~2-5k tokens,
   representative of a real Claude Code system prompt + tool defs) twice within a few
   seconds, varying only the trailing user message. Compare
   `resp.usage.prompt_tokens_details.cached_tokens` between the two calls. Non-zero and
   growing on repeat = automatic prefix caching exists on this endpoint today.
2. **Responses API model compatibility.** Check whether `qwen.qwen3-coder-30b-a3b-v1:0`
   and `qwen.qwen3-coder-next` support the Responses API at all — via `GET /v1/models`
   output and/or AWS's `models-api-compatibility` page. Bedrock Mantle's own docs warn not
   all models support it.
3. **Responses API statefulness benefit** (only if question 2 is yes). Send an initial
   `client.responses.create(...)`, then a follow-up passing `previous_response_id` instead
   of resending history. Compare latency and `usage` token counts against sending the
   equivalent full-history request cold. This distinguishes "skips recomputation" from
   "just avoids resending bytes over the wire."

**Output:** a findings note (appended to this spec, dated) stating yes/no and the raw
numbers for each of the three questions. This is the fork point for everything below.

## Decision branches

### Path A — Chat Completions auto-caching confirmed (question 1 = yes)

No protocol switch needed — the destination already caches; the work is to stop
accidentally defeating it and start measuring it.

- Audit `_anthropic_to_openai_request` for non-determinism that would break byte-identical
  prefixes across turns: dict/key ordering, any injected timestamps or request IDs,
  floating-point serialization differences.
- Surface `cached_tokens` into usage tracking (the path that calls
  `record_usage_from_openai_response`) so cache-hit rate becomes an ongoing observable
  metric rather than a one-off spike finding.
- Add a regression test asserting the translator produces byte-identical JSON for two
  calls sharing a logical prefix but differing in the trailing message.

### Path B — Responses API supported by these models AND shows a real reuse benefit (questions 2 and 3 = yes)

A genuine protocol migration for these two tiers, not a caching feature — too large for
this plan to implement end-to-end. This branch produces its own follow-up spec plus a Tech
Design Review (per this repo's org-wide baseline instructions, given it introduces a new
architectural pattern and a PHI/data-retention question) rather than proceeding directly to
an implementation plan. That follow-up spec needs to cover at minimum:

- New Anthropic ↔ Responses translator functions (`input` shape in, event/response shape
  out), parallel to — not replacing — the existing chat.completions translator, so
  non-migrated routes are unaffected.
- A session-state bridge: Claude Code always resends full history every turn; the router
  would need to detect conversation continuation (likely via the existing
  `session_id`/`account_directory` machinery), track the last `response_id` per session,
  and forward only the new trailing turn upstream.
- PHI/retention handling: Responses API defaults to `store=true`, retaining request/response
  content in Bedrock for 30 days. Using statefulness while setting `store=false` on every
  request is self-defeating (no `previous_response_id` continuation without stored state),
  so this needs either an explicit risk acceptance for a HIPAA-scoped platform or a
  documented compliance sign-off before implementation — not something to decide inside an
  implementation plan.
- New streaming/error-handling logic for the Responses API's own event shapes, separate
  from the `stream_converter.py`/`_handle_unexpected_upstream_error` work already in place
  for chat.completions.

### Path C — Neither shows anything (questions 1-3 = no)

Document the spike findings in this spec and close this initiative out. Do not build a
speculative fallback (see Non-goals) — there is no viable caching lever on this endpoint
today. Revisit only if AWS documents a caching mechanism for Bedrock Mantle in the future.

## Risks

- **Phase 0 findings could be non-obvious to interpret** — e.g. `cached_tokens` could be
  present in the schema but always `0` for these specific models even if the *mechanism*
  exists for others; treat a zero result as "no observed benefit for our models," not
  "definitively no caching capability at Bedrock Mantle at all."
- **Path A's determinism audit could surface unrelated instability** in
  `_anthropic_to_openai_request` that has nothing to do with caching (e.g. genuinely
  non-deterministic request bodies causing other, unrelated bugs) — treat any such finding
  as its own bug report, not scope creep into this plan.
- **Path B is a large enough initiative that estimating it accurately from this document
  alone is not realistic** — the bullet list above is a starting outline for its own spec,
  not a committed implementation scope.

## Phase 0 findings (2026-07-13)

**Question 1 — Chat Completions caching signal:**

Final, isolated run (all 12 calls — 2 models × 3 variants × 2 calls each — using
`qwen.qwen3-coder-30b-a3b-v1:0` and `qwen.qwen3-coder-next`):

| model | variant | call 0 `cached_tokens` | call 1 `cached_tokens` |
|---|---|---|---|
| qwen.qwen3-coder-30b-a3b-v1:0 | no cache params | None | None |
| qwen.qwen3-coder-30b-a3b-v1:0 | prompt_cache_key set | None | None |
| qwen.qwen3-coder-30b-a3b-v1:0 | prompt_cache_retention=24h | None | None |
| qwen.qwen3-coder-next | no cache params | None | None |
| qwen.qwen3-coder-next | prompt_cache_key set | None | None |
| qwen.qwen3-coder-next | prompt_cache_retention=24h | None | None |

Every one of the 12 calls returned `cached_tokens=None` — no evidence of any caching
benefit, with or without `prompt_cache_key` or `prompt_cache_retention=24h`.

Earlier runs of this same spike showed sporadic, ambiguous `cached_tokens` hits (e.g. a
hit on the first call of a variant, before any repeat had even executed). These were
traced to a methodology flaw, not real caching: OpenAI-style automatic prompt caching
matches on longest-common-prefix, and the uniqueness markers used to isolate runs and
variants from each other were appended to the *end* of the shared ~2-5k-token prefix
rather than the front. That left a large shared *leading* block — identical across every
run, every variant, and every model, ever executed against this endpoint under this
account — free to prefix-match and produce apparent "hits" that had nothing to do with
the variant under test. Once the uniqueness markers were moved to the front of the
prefix (so every call's prompt diverges from every other call's at the very first token),
every one of the 12 calls in this final run came back `cached_tokens=None`, and no
ambiguous hit reproduced. This final, front-loaded-marker run is the trustworthy result;
the earlier ambiguous hits should not be treated as evidence of real caching behavior.

**Question 2 — Responses API model compatibility:**

Both models: **NOT SUPPORTED**. Bedrock Mantle rejects Responses API calls for both
models with an explicit HTTP 400 `validation_error`:

- `qwen.qwen3-coder-30b-a3b-v1:0`:
  `BadRequestError: Error code: 400 - {'error': {'code': 'validation_error', 'message': "The model 'qwen.qwen3-coder-30b-a3b-v1:0' does not support the '/v1/responses' API", 'param': None, 'type': 'invalid_request_error'}}`
- `qwen.qwen3-coder-next`:
  `BadRequestError: Error code: 400 - {'error': {'code': 'validation_error', 'message': "The model 'qwen.qwen3-coder-next' does not support the '/v1/responses' API", 'param': None, 'type': 'invalid_request_error'}}`

**Question 3 — previous_response_id statefulness benefit:**

Not applicable — neither model supports the Responses API (see Question 2), so this task
was skipped per the plan.

**Conclusion:** **Path C.** Question 1 shows no observed caching benefit on the Chat
Completions endpoint for either model (all 12 calls in the final, methodologically clean
run returned `cached_tokens=None`), and Question 2 shows neither model even supports the
Responses API, which forecloses Question 3 entirely. With both avenues negative, there is
no viable caching lever on this endpoint today for `haiku`/`sonnet` traffic — this
initiative is closed out per Path C, with no speculative gateway-side response caching
built (see Non-goals). Revisit only if AWS documents a caching mechanism for Bedrock
Mantle in the future.
