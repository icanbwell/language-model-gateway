import json
import logging
import os
import sys
import traceback
from typing import override

TEXT_FORMAT = "%(asctime)s %(levelname)s %(name)s [%(filename)s:%(lineno)d] %(message)s"


class JsonLogFormatter(logging.Formatter):
    """Formats each log record as a single-line JSON object.

    Groundcover (and other line-oriented log shippers) treats every newline
    in stdout as a separate log entry. Emitting one JSON object per record —
    with multi-line messages and exception tracebacks folded into string
    fields rather than left as raw embedded newlines — keeps each logical
    log event as exactly one line.
    """

    @override
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "file": record.filename,
            "line": record.lineno,
        }
        if record.exc_info:
            payload["exception"] = "".join(traceback.format_exception(*record.exc_info))
        extra_fields = getattr(record, "extra_fields", None)
        if extra_fields:
            payload.update(extra_fields)
        return json.dumps(payload, default=str)


def build_log_handler() -> logging.Handler:
    handler = logging.StreamHandler(sys.stdout)
    if os.environ.get("LOG_FORMAT", "json").lower() == "text":
        handler.setFormatter(logging.Formatter(TEXT_FORMAT))
    else:
        handler.setFormatter(JsonLogFormatter())
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
