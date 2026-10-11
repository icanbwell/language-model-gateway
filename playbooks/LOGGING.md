# Logging

Last verified: 2026-10-11 against b0d7252b by Claude

How this repo logs. Org-wide rules (never log PHI or credentials; single-line JSON for Groundcover) live in the wiki's `standards/observability/` and the org logging standard; this file covers how this repo applies them. Locations: [MONITORING.md](MONITORING.md). Signals: [TROUBLESHOOTING.md](TROUBLESHOOTING.md).

## Logger and format

Stdlib `logging.getLogger(__name__)` everywhere, rendered to one JSON object per line by structlog's `ProcessorFormatter` (`language_model_gateway/gateway/utilities/logger/log_levels.py`; decision in [adrs/0001-structlog-for-json-log-rendering.md](../adrs/0001-structlog-for-json-log-rendering.md)). `LOG_FORMAT=text` selects plain text. The app calls `logging.basicConfig(..., force=True, handlers=[build_log_handler()])` at startup with `LOG_LEVEL` defaulting to INFO (`language_model_gateway/gateway/api.py`), so JSON is the default format.

## Levels

Global level `LOG_LEVEL`; per-source overrides `<SOURCE>_LOG_LEVEL` for the sources listed in `log_levels.py`. The repo does not define a written rule for ERROR versus WARNING; the Copilot guideline is to use `logger.exception` inside `except` blocks (`.github/copilot-instructions.md`). One-ERROR-per-failure is not enforced: a failed HTTP request writes two ERROR messages in the middleware.

## Required fields

| Field | Meaning | Set in | Used by |
|---|---|---|---|
| `timestamp` | local time at `%Y-%m-%dT%H:%M:%S%z` | `_extract_stdlib_fields` | Groundcover |
| `level` | record level name | same | Groundcover |
| `logger` | logger name | same | Groundcover |
| `file`, `line` | source location | same | Groundcover |
| `message` | the formatted message | `_finalize_message_and_extras` | Groundcover |
| `exception` | folded traceback | `_extract_stdlib_fields` | Groundcover |
| `extra_fields` keys | merged last and can override the core fields | `_finalize_message_and_extras` | none known |

The record carries no request id, session id or trace id field (verified in `log_levels.py`); trace correlation, if any, is unverified. No dashboard or monitor dependency is known (unverified); renaming a field is still a breaking change for ad-hoc queries, so update MONITORING.md in the same PR. Person and patient identifiers may appear in logs as fields where needed; never write real values into any file.

## Per-request and per-failure lines

No single per-request line exists. `FastApiLoggingMiddleware` logs only responses with status 300 or above at ERROR (two messages per failure) and everything else at DEBUG; `/health` is skipped. Count failed requests by the `Response ERROR` message, not by the request message.

## Latency and timing

Only the middleware reports time: `(time: N.NNNN secs)` inside the response message, covering `call_next` for the whole request (`fastapi_logging_middleware.py`). It is text in the message, not a field. For streaming responses it measures time to the first chunk, not the full stream (unverified; the iterator is re-chained after timing).

## Error classification

No bounded error-class set exists in this repo (no such field or enum found in `log_levels.py` or the middleware).

## Never log

- Authorization headers, JWTs, S3 paths with PHI, OpenWebUI user details (`.github/copilot-instructions.md`).
- Known exception: at status 300 or above the middleware always logs request headers (including Authorization) and the request body at ERROR, regardless of level; the response body is logged only when DEBUG is enabled for `HTTP_TRACING_LOG_LEVEL`, otherwise the line reads `No body`. At DEBUG it also logs headers and bodies for every request (`fastapi_logging_middleware.py`). Treat these lines as carrying credentials and PHI risk; do not copy them into any file or report. A safe summarizer (type, length, key names) is not implemented. No test enforces a no-PHI rule (`none; reviewer only`).

## When you change logging

- Level choice and `logger.exception` in `except` blocks hold.
- Fields above keep their names, or MONITORING.md is updated in the same PR.
- No PHI, tokens or full bodies.
- A new signal responders should look for goes in TROUBLESHOOTING.md.
- Tests for formatter behavior: `tests/gateway/utilities/logger/test_log_levels.py`, `tests/gateway/middleware/test_fastapi_logging_middleware.py`.
