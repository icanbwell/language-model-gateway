---
status: accepted
date: 2026-07-10
---

# Use structlog to render single-line JSON logs

## Context and Problem Statement

The app logs via stdlib `logging` everywhere (`logging.getLogger(__name__)`).
Groundcover ingests one log entry per newline in stdout, so a previous fix
introduced a hand-rolled `JsonLogFormatter(logging.Formatter)` that folded
each `LogRecord` (message, exception traceback, arbitrary `extra_fields`)
into one JSON object per line.

We want to replace that hand-rolled formatter with `structlog`'s JSON
rendering instead of maintaining custom JSON-building code, without
rewriting the hundreds of existing `logger.info(...)` call sites across the
codebase.

## Decision Drivers

* Minimal diff: every call site uses stdlib `logging`; a migration that
  requires touching all of them is out of scope and high-risk.
* Preserve the existing Groundcover-facing JSON schema exactly
  (`timestamp`, `level`, `logger`, `message`, `file`, `line`, `exception`,
  plus merged `extra_fields`) so no dashboards/alerts/queries break.
* `structlog` is not in `policies/approved-tech.yaml` (observability
  category, `severity: warn`) — flagged here per EA policy; a Tech Design
  Review ticket should be opened before this lands on `main`.

## Considered Options

* **Option A — Keep the hand-rolled `JsonLogFormatter`.** Zero new
  dependency, but we hand-maintain JSON construction, exception
  formatting, and any future field additions ourselves.
* **Option B — Adopt `structlog`'s `stdlib.ProcessorFormatter` as a
  drop-in `logging.Formatter`.** All existing `logging.getLogger(...)`
  call sites are unaffected; `ProcessorFormatter` treats every record as
  "foreign" (not structlog-native) and runs it through a
  `foreign_pre_chain` + `processors` pipeline before rendering with
  `structlog.processors.JSONRenderer`. Only `log_levels.py` changes.
* **Option C — Full structlog migration** (`structlog.get_logger()`
  everywhere, structured `log.info("msg", key=val)` call sites). Correct
  long-term direction for a codebase built around structlog from day one,
  but requires touching every logging call site in the app — violates
  Minimal Diff for this change and is a much larger, separate effort.

## Decision Outcome

Chosen option: **"Option B — `structlog.stdlib.ProcessorFormatter`"**,
because it gets us onto `structlog` (per the stated goal of moving off the
hand-rolled formatter) while keeping the change scoped to
`language_model_gateway/gateway/utilities/logger/log_levels.py`. Every
other file keeps calling `logging.getLogger(__name__)` / `logger.info(...)`
exactly as before.

Implementation notes:
* `_extract_stdlib_fields` (a `foreign_pre_chain` processor) reads the raw
  `LogRecord` off `event_dict["_record"]` and sets `timestamp`, `level`,
  `logger`, `file`, `line`, and `exception` (folded traceback) — mirroring
  the old formatter's `format()` method field-for-field.
* `ProcessorFormatter` seeds `event_dict["exc_info"] = record.exc_info`
  for records with a traceback; left unremoved, it leaks the raw
  `(type, value, traceback)` tuple into the rendered JSON as a `default=str`
  stringified list. `_extract_stdlib_fields` pops it after converting to
  the `exception` string field. A regression test
  (`test_json_log_formatter_folds_exception_into_single_line`) asserts
  `"exc_info" not in payload`.
* `extra_fields` is merged as the *last* step
  (`_finalize_message_and_extras`), after `event`→`message` renaming, so
  it can still override any core field — matching the old formatter's
  `payload.update(extra_fields)` being the final line of `format()`.
* `LOG_FORMAT=text` keeps using the plain `logging.Formatter(TEXT_FORMAT)`
  path unchanged — this ADR only touches the JSON path.

### Consequences

* Good: no more hand-maintained JSON-construction code; get structlog's
  battle-tested processor pipeline (and room to add more processors later
  — e.g. request-context binding — without touching call sites).
* Good: schema-compatible — verified via unit tests
  (`tests/gateway/utilities/logger/test_log_levels.py`) that assert on the
  exact same fields the old formatter produced.
* Neutral: adds `structlog` as a new runtime dependency
  (`pyproject.toml`); not yet in `policies/approved-tech.yaml` — flagging
  for Tech Design Review per EA policy (severity: warn, non-blocking).
* Neutral: does not move the app toward structlog-native structured
  logging (`log.info("msg", key=val)`); that's Option C, deliberately out
  of scope here.
