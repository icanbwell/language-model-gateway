# Native Bedrock transport as a fallback for Bedrock Mantle

## Context

The coding model router (`language_model_gateway/gateway/routers/model_routing/`) routes
Claude Code traffic for the haiku/sonnet tiers to Qwen coder models hosted behind
**Bedrock Mantle** — AWS's OpenAI-compatible shim in front of Bedrock — using
`openai.AsyncOpenAI` with SigV4 signing (`route["auth"] == "aws"`,
`route["api_type"] == "openai"`, `route["url"]` pointing at
`bedrock-mantle.us-east-1.api.aws`).

Bedrock Mantle has surfaced generic, unhelpful 500 errors
(`{"code": "internal_server_error", "message": "The server had an error while
processing your request. Sorry about that!", ...}`) with no further diagnostic
detail available from the SDK exception object. This is a known reliability gap in
Mantle itself, not a bug in this codebase's error capture (verified: the existing
capture code in `router.py` already records `exc.message`/`code`/`type`/`param`/`body`
verbatim; there is nothing more to extract from a bare `openai.APIError`).

This design adds a manual, env-var-controlled fallback: the ability to route the same
haiku/sonnet traffic to the **same Qwen models** via Bedrock's native Converse API
instead of Mantle, so on-call can flip a single switch during a Mantle incident.

## Goals

- A single global env var, `MODEL_ROUTING_BEDROCK_TRANSPORT` (`"mantle"` default /
  `"native"`), controls transport for all `auth == "aws"` routes at once.
- Same model IDs (`qwen.qwen3-coder-30b-a3b-v1:0`, `qwen.qwen3-coder-next`) — only the
  transport layer changes, not the model or its cost profile.
- No automatic failover, no per-route/per-tier granularity — this is an operator-flipped
  static toggle for an incident, not a runtime retry policy.
- No new dependency: `boto3` is already used (`aws_auth.py`) and
  `types-boto3-bedrock-runtime` is already a dev dependency.

## Non-goals

- Automatic detection-and-failover from Mantle to native Bedrock mid-request.
- Support for arbitrary non-Qwen models on the native path.
- Changing the Anthropic-facing wire contract that Claude Code clients see — streaming
  event sequence and non-streaming response shape must be identical regardless of
  transport.

## Architecture

`MODEL_ROUTING_BEDROCK_TRANSPORT` is read via the `EnvironmentVariables` DI class
(`LanguageModelGatewayEnvironmentVariables` in
`language_model_gateway_environment_variables.py`), not a bare module-level
`os.environ.get()` in the `model_routing/` package. A new
`model_routing_bedrock_transport` property is added there, following the exact
convention already used for every other model-routing setting (e.g.
`model_routing_error_collection_name`, `model_routing_usage_collection_name`):

```python
@property
def model_routing_bedrock_transport(self) -> str:
    return os.environ.get("MODEL_ROUTING_BEDROCK_TRANSPORT", "mantle")
```

`api.py:create_app()` already resolves `env_vars =
container.resolve(LanguageModelGatewayEnvironmentVariables)` and passes individual
`model_routing_*` settings into `CodingModelRouter(...)` as constructor kwargs (see
`usage_collection_name`, `error_collection_name`, etc.). This value follows the same
path: `bedrock_transport=env_vars.model_routing_bedrock_transport` is added to that
constructor call, and `CodingModelRouter.__init__` stores it as `self._bedrock_transport`.
This is the first `model_routing_*` setting the package itself doesn't read directly —
but that's consistent with, not a departure from, how every sibling setting already
flows in from `api.py`.

In `router.py`, the existing `if api_type == "openai":` branch gains one more
condition: when `self._bedrock_transport == "native"` for an `auth == "aws"` route,
dispatch to a new module, `bedrock_converse_client.py`, instead of constructing an
`openai.AsyncOpenAI` client. Every other route (Opus/Fable passthrough to Anthropic, and
Mantle when the toggle is at its default) is unaffected.

`bedrock_converse_client.py` sits alongside `bedrock_client.py` (httpx passthrough +
retry helpers) and `aws_auth.py` (SigV4 signing, credential-error mapping), each keeping
one responsibility:

- Builds and caches a `boto3` `bedrock-runtime` client per `(profile, region)` — boto3
  clients are thread-safe and reusable, so a request-scoped client is avoided.
- Converts Anthropic request/response format to/from Bedrock's Converse format.
- Adapts boto3's synchronous `converse`/`converse_stream` calls onto the asyncio event
  loop via `asyncio.to_thread`.

Converse (not raw `InvokeModel`) is the chosen native API because it has a unified,
model-agnostic message and tool-use shape. This router leans heavily on tool use —
`message_translator.py` already converts Anthropic `tool_use`/`tool_result` blocks in
both directions for Claude Code — and `InvokeModel` would mean a Qwen-specific wire
format instead of one shared shape.

### Rejected alternative

Raw `httpx` + manual SigV4 against the `bedrock-runtime` REST endpoint, reusing
`_send_with_bedrock_retry`/`SigV4Auth` unchanged. Rejected because Bedrock's native HTTP
streaming responses use AWS's binary `vnd.amazon.eventstream` framing, not plain SSE.
boto3 already decodes that; reimplementing that decoder for no benefit over calling
boto3 directly isn't worth the risk.

## Data flow

### Non-streaming

**Deviation from this section as originally written:** the shipped function is
`_openai_to_converse_request(oai_body_json, model_id)`, not `_anthropic_to_converse_request`.
It builds boto3 kwargs from the already-OpenAI-Chat-Completions-shaped, context-budget-
enforced request body (as produced by `message_translator.py`'s
`_anthropic_to_openai_request`), not the raw Anthropic request — `router.py`'s dispatch
runs context-budget enforcement upstream of the native-Bedrock branch, and that
enforcement only understands the OpenAI shape, so converting from the original Anthropic
request would bypass it. The field mapping itself is unchanged from what's described
below, just sourced from OpenAI-shaped fields (`messages[].role/content/tool_calls`,
`tools`/`tool_choice`) instead of Anthropic ones.

`_openai_to_converse_request(oai_body_json, model_id)` builds boto3 kwargs:

- `modelId` = `model_id`
- `messages`: OpenAI `messages` → Converse block shape
  (`{"role": ..., "content": [{"text": ...} | {"toolUse": {...}} | {"toolResult": {...}}]}`)
- `system` → `[{"text": ...}]`
- `inferenceConfig` → `{"maxTokens", "temperature", "topP"}`
- `toolConfig` → `{"tools": [...], "toolChoice": ...}` from OpenAI `tools`/`tool_choice`

`_converse_response_to_anthropic(resp, msg_id, upstream_model)` mirrors
`_openai_to_anthropic_response`: reads `resp["output"]["message"]["content"]` blocks,
`resp["stopReason"]`, `resp["usage"]` into the Anthropic response shape. Both boto3 calls
run via `asyncio.to_thread`.

### Streaming

`converse_stream()` returns a synchronous `EventStream`
(`messageStart`/`contentBlockStart`/`contentBlockDelta`/`contentBlockStop`/`messageStop`/`metadata`).
An adapter pulls each event off that iterator via `asyncio.to_thread` and yields it as an
async generator. `_stream_bedrock_converse_to_anthropic(events, msg_id, upstream_model, ...)`
translates each event into the same Anthropic SSE sequence
(`message_start`/`content_block_start`/`content_block_delta`/`content_block_stop`/`message_delta`/`message_stop`)
that `stream_converter.py::_stream_oai_sdk_to_anthropic` already emits for the Mantle
path, so the existing `on_stream_error`/usage-tracking hooks in `router.py` require no
changes.

## Error handling

Wrap both the initial `converse`/`converse_stream` call and the per-event thread pull:

- **`botocore.exceptions.ClientError`** — carries `.response["Error"]["Code"]`/`["Message"]`
  and `.response["ResponseMetadata"]["RequestId"]`. Match `Error.Code` against the
  existing `_TRANSIENT_STREAM_ERROR_CODES` in `bedrock_client.py` (already lists native
  Bedrock exception names — `ThrottlingException`, `ModelStreamErrorException`, etc.) to
  decide retry-with-backoff, reusing `_throttle_backoff`.
- **Credential errors** (`NoCredentialsError`, `TokenRetrievalError`) — reuse
  `_bedrock_credential_error_detail` from `aws_auth.py` unchanged, so the
  credential-failure UX matches the Mantle path.
- **Connection-level failures** (`EndpointConnectionError`, `ConnectTimeoutError`) —
  transient, same backoff/retry treatment as `httpx.TransportError` in
  `bedrock_client.py`.

All errors are recorded via the existing `_record_error` helper with
`error_type="bedrock_native_error"` and `error_message` = JSON of
`{"code", "message", "request_id"}`. The AWS request ID here is diagnostic detail the
Mantle mid-stream error path never provides — a direct improvement over the case
debugged earlier.

## Testing

- Conversion unit tests for `_anthropic_to_converse_request` /
  `_converse_response_to_anthropic`, parameterized over plain text, tool_use round-trip,
  tool_result, multi-turn, and system-prompt cases — mirroring existing coverage for
  `_anthropic_to_openai_request`/`_openai_to_anthropic_response`.
- Streaming-adapter unit test using a fake synchronous iterator standing in for boto3's
  `EventStream`, verifying ordered async yielding and exception propagation.
- Router-level tests mocking `boto3.client("bedrock-runtime")` at the boundary (no real
  AWS calls in CI): construct `CodingModelRouter(..., bedrock_transport="native")`
  directly (mirroring how existing router tests already pass other
  constructor-injected `model_routing_*` settings) and verify haiku/sonnet route through
  the new path while the `mantle` default is unaffected, and that the emitted Anthropic
  SSE sequence matches the existing Mantle-path output.
- A test for the new `model_routing_bedrock_transport` property on
  `LanguageModelGatewayEnvironmentVariables`, and confirmation that `api.py:create_app()`
  threads it into `CodingModelRouter(...)` as `bedrock_transport=...`.
- Error-path tests: transient `ClientError` codes retried; non-transient codes recorded
  via `_record_error` with `bedrock_native_error` and the AWS request ID surfaced to the
  client.
- Manual smoke test (not CI, before relying on this in an incident): confirm
  `qwen.qwen3-coder-30b-a3b-v1:0` and `qwen.qwen3-coder-next` are actually invocable via
  native Bedrock's Converse API in `us-east-1` — this design assumes that; it isn't
  verifiable from code alone.
