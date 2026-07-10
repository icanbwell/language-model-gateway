import json
import logging
import os
import sys
import time
import traceback

import structlog
from structlog.typing import EventDict, WrappedLogger

TEXT_FORMAT = "%(asctime)s %(levelname)s %(name)s [%(filename)s:%(lineno)d] %(message)s"


def _extract_stdlib_fields(
    logger: WrappedLogger, method_name: str, event_dict: EventDict
) -> EventDict:
    """Pull the fields Groundcover expects out of the raw stdlib LogRecord.

    Every logger in this app is a plain `logging.getLogger(...)`, so every
    record structlog sees here is "foreign" — this pre-chain processor is
    what turns it into our JSON schema before rendering.
    """
    record: logging.LogRecord = event_dict["_record"]
    event_dict["timestamp"] = time.strftime(
        "%Y-%m-%dT%H:%M:%S%z", time.localtime(record.created)
    )
    event_dict["level"] = record.levelname
    event_dict["logger"] = record.name
    event_dict["file"] = record.filename
    event_dict["line"] = record.lineno
    if record.exc_info:
        event_dict["exception"] = "".join(traceback.format_exception(*record.exc_info))
    event_dict.pop("exc_info", None)
    event_dict["_extra_fields"] = getattr(record, "extra_fields", None)
    return event_dict


def _finalize_message_and_extras(
    logger: WrappedLogger, method_name: str, event_dict: EventDict
) -> EventDict:
    """Rename structlog's `event` key to `message` and merge extra_fields last.

    Merging last (rather than in `_extract_stdlib_fields`) preserves the
    original formatter's semantics: extra_fields can override any of the
    core fields set above, since it is applied after them.
    """
    event_dict["message"] = event_dict.pop("event", "")
    extra_fields = event_dict.pop("_extra_fields", None)
    if extra_fields:
        event_dict.update(extra_fields)
    return event_dict


def build_json_log_formatter() -> logging.Formatter:
    """Formats each log record as a single-line JSON object via structlog.

    Groundcover (and other line-oriented log shippers) treats every newline
    in stdout as a separate log entry. Emitting one JSON object per record —
    with multi-line messages and exception tracebacks folded into string
    fields rather than left as raw embedded newlines — keeps each logical
    log event as exactly one line.
    """
    return structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=[_extract_stdlib_fields],
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            _finalize_message_and_extras,
            structlog.processors.JSONRenderer(serializer=json.dumps, default=str),
        ],
    )


def build_log_handler() -> logging.Handler:
    handler = logging.StreamHandler(sys.stdout)
    if os.environ.get("LOG_FORMAT", "json").lower() == "text":
        handler.setFormatter(logging.Formatter(TEXT_FORMAT))
    else:
        handler.setFormatter(build_json_log_formatter())
    return handler


GLOBAL_LOG_LEVEL = os.environ.get("LOG_LEVEL", "").upper()
if GLOBAL_LOG_LEVEL in logging.getLevelNamesMapping():
    logging.basicConfig(
        level=GLOBAL_LOG_LEVEL,
        force=True,
        handlers=[build_log_handler()],
    )
else:
    GLOBAL_LOG_LEVEL = "INFO"

log = logging.getLogger(__name__)
log.info(f"GLOBAL LOG_LEVEL: {GLOBAL_LOG_LEVEL}")

log_sources = [
    "HTTP_TRACING",
    "CONFIG",
    "INITIALIZATION",
    "HTTP",
    "AUTH",
    "TOKEN_EXCHANGE",
    "DATABASE",
    "LLM",
    "FILES",
    "IMAGE_GENERATION",
    "IMAGE_PROCESSING",
    "MCP",
    "AGENTS",
    "ERRORS",
    "BAILEY",
]

SRC_LOG_LEVELS = {}

for source in log_sources:
    log_env_var = source + "_LOG_LEVEL"
    SRC_LOG_LEVELS[source] = os.environ.get(log_env_var, "").upper()
    if SRC_LOG_LEVELS[source] not in logging.getLevelNamesMapping():
        SRC_LOG_LEVELS[source] = GLOBAL_LOG_LEVEL
    log.info(f"{log_env_var}: {SRC_LOG_LEVELS[source]}")
