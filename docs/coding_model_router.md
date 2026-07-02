# CodingModelRouter

Routes Anthropic Messages API requests to either **Anthropic direct** (passthrough)
or **AWS Bedrock** based on a JSON config keyed by model name.

---

## Overview

`CodingModelRouter` is a FastAPI router that proxies requests arriving in the
Anthropic Messages API wire format.  Clients (e.g. Claude Code, Claude Desktop,
the Anthropic SDK) point their `ANTHROPIC_BASE_URL` at this gateway and send
requests exactly as they would to `api.anthropic.com`.  The router:

1. Reads the `model` field from the request body.
2. Looks up the model name in a local route config file.
3. Forwards the request to the configured upstream (Anthropic or Bedrock).
4. Streams the response back verbatim, or translates it when the upstream
   speaks OpenAI Chat Completions format.

---

## Registered endpoints

| Method | Path                        | Description                              |
|--------|-----------------------------|------------------------------------------|
| `POST` | `/v1/messages`              | Proxy Anthropic Messages API             |
| `POST` | `/v1/messages/count_tokens` | Proxy Anthropic token-count endpoint     |

For `api_type: openai` routes, `/v1/messages/count_tokens` is not forwarded
upstream; the router returns a rough estimate (`len(body_json) / 4`) instead.

---

## Environment variables

| Variable        | Default                                    | Description                                      |
|-----------------|--------------------------------------------|--------------------------------------------------|
| `ROUTER_CONFIG` | `~/model-router/router_config.json`        | Path to the route config JSON file               |
| `AWS_PROFILE`   | *(none)*                                   | AWS profile used when signing Bedrock requests   |

In `docker-compose.yml` this is set to:
```
ROUTER_CONFIG: /usr/src/language_model_gateway/language-model-gateway-configs/model-router-config.json
```
which resolves via the existing `./:/usr/src/language_model_gateway/` volume mount to
`language-model-gateway-configs/model-router-config.json` in the repo root.

---

## Route config file

The config file is a JSON object with a `routes` array.  Each entry maps a
Claude model name (as sent by the client) to an upstream destination.

### Schema

```jsonc
{
  "routes": [
    {
      // Required fields
      "claude_model": "claude-sonnet-4-6",   // model name the client sends
      "url":          "https://...",          // upstream URL
      "model":        "upstream-model-id",   // model name forwarded to upstream
      "auth":         "passthrough" | "aws", // auth strategy (see below)

      // Optional fields
      "api_type":     "anthropic" | "openai", // wire protocol (default: "anthropic")
      "aws_region":   "us-east-1"             // AWS region for Bedrock (default: "us-east-1")
    }
  ]
}
```

If the config file is not found, the router logs a warning and falls back to
Anthropic direct for all requests.

If a model is not listed in `routes`, the router also falls back to Anthropic
direct, forwarding the client's `Authorization` header unchanged.

### Auth strategies

| Value         | Behaviour                                                                               |
|---------------|-----------------------------------------------------------------------------------------|
| `passthrough` | Forwards the client's `Authorization` header to the upstream as-is (Anthropic direct). |
| `aws`         | Signs each request with AWS SigV4 (for Bedrock). No auth header is forwarded.          |

### API types

| Value       | Behaviour                                                                                           |
|-------------|-----------------------------------------------------------------------------------------------------|
| `anthropic` | Upstream speaks Anthropic Messages API; bytes are forwarded verbatim.                              |
| `openai`    | Upstream speaks OpenAI Chat Completions API (e.g. Bedrock Mantle); request is translated from Anthropic format and response translated back. |

---

## Example configs

### Anthropic direct passthrough

```json
{
  "routes": [
    {
      "claude_model": "claude-sonnet-4-6",
      "url":          "https://api.anthropic.com/v1/messages",
      "model":        "claude-sonnet-4-6",
      "auth":         "passthrough"
    }
  ]
}
```

### AWS Bedrock — Anthropic format

```json
{
  "routes": [
    {
      "claude_model": "claude-sonnet-4-6",
      "url":          "https://bedrock-runtime.us-east-1.amazonaws.com/model/anthropic.claude-3-5-sonnet-20241022-v2:0/invoke",
      "model":        "anthropic.claude-3-5-sonnet-20241022-v2:0",
      "auth":         "aws",
      "api_type":     "anthropic",
      "aws_region":   "us-east-1"
    }
  ]
}
```

### AWS Bedrock — OpenAI-compatible endpoint (Bedrock Mantle)

```json
{
  "routes": [
    {
      "claude_model": "claude-sonnet-4-6",
      "url":          "https://bedrock-runtime.us-east-1.amazonaws.com/v1/chat/completions",
      "model":        "us.anthropic.claude-3-5-sonnet-20241022-v2:0",
      "auth":         "aws",
      "api_type":     "openai",
      "aws_region":   "us-east-1"
    }
  ]
}
```

---

## Request translation (`api_type: openai`)

When `api_type` is `openai`, the router translates the Anthropic request body
to OpenAI Chat Completions format before forwarding, and translates the
response back to Anthropic format before returning it to the client.

Translated fields:

| Anthropic request field      | OpenAI equivalent                   |
|------------------------------|-------------------------------------|
| `system`                     | `messages[0]` with `role: system`   |
| `messages[].content[]` (text)| `messages[].content` (string)       |
| `messages[].content[]` (image)| `messages[].content[].image_url`   |
| `messages[].content[]` (tool_use) | `messages[].tool_calls`        |
| `messages[].content[]` (tool_result) | `messages[]` with `role: tool` |
| `tools[].input_schema`       | `tools[].function.parameters`       |
| `tool_choice: any`           | `tool_choice: required`             |

Thinking blocks (`<think>…</think>`) emitted by reasoning models are stripped
from both streaming and non-streaming responses before they are returned to the
client.

---

## Throttle retry and backoff

For `auth: aws` routes, the router automatically retries on throttling
responses (HTTP 429 or bodies matching common Bedrock throttle messages):

| Parameter           | Value                 |
|---------------------|-----------------------|
| Max retries         | 5                     |
| Base delay          | 1 s                   |
| Max delay           | 20 s                  |
| Backoff             | Exponential with jitter |
| Dispatch pacing     | 300 ms minimum between requests |

Context-overflow errors (Bedrock reports that the prompt exceeds the model's
context window) are not retried and are surfaced immediately.  For
`api_type: openai` streaming requests, the router additionally halves
`max_tokens` up to four times before giving up.

---

## Error handling

Upstream errors (4xx/5xx) are returned to the client with the original status
code and body.

AWS credential errors (`TokenRetrievalError`) and other infrastructure errors
are surfaced as a valid Anthropic assistant message with `stop_reason:
end_turn`, so that streaming clients receive a well-formed response rather than
a broken stream.  The error text is included in the assistant message content
to aid debugging.

---

## Integration with the gateway

`CodingModelRouter` is registered in `language_model_gateway/gateway/api.py`
at startup with the default prefix `/v1`:

```python
app1.include_router(CodingModelRouter().get_router())
```

No authentication middleware is applied to this router at the FastAPI layer.
Auth is handled implicitly: `passthrough` routes relay the client's
`Authorization` header to Anthropic, and `aws` routes use SigV4 signing.

---

## Configuring a client to use the router

Set `ANTHROPIC_BASE_URL` (and optionally `ANTHROPIC_API_KEY`) to point at the
gateway host.

**Anthropic SDK (Python)**

```python
import anthropic

client = anthropic.Anthropic(
    base_url="http://localhost:4000",   # gateway host
    api_key="dummy",                    # required by the SDK; ignored for aws routes
)
```

**Claude Code / Claude Desktop**

```sh
export ANTHROPIC_BASE_URL=http://localhost:4000
export ANTHROPIC_API_KEY=your-real-key   # only needed for passthrough routes
```

The client sends requests to `/v1/messages` exactly as it would to
`api.anthropic.com`.  The router rewrites the destination based on the config
file without any change to the client-side request format.
