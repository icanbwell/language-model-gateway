import logging
import os
import sys

GLOBAL_LOG_LEVEL = os.environ.get("LOG_LEVEL", "").upper()
if GLOBAL_LOG_LEVEL in logging.getLevelNamesMapping():
    logging.basicConfig(
        stream=sys.stdout,
        level=GLOBAL_LOG_LEVEL,
        force=True,
        format="%(asctime)s %(levelname)s %(name)s [%(filename)s:%(lineno)d] %(message)s",
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
]

SRC_LOG_LEVELS = {}

for source in log_sources:
    log_env_var = source + "_LOG_LEVEL"
    SRC_LOG_LEVELS[source] = os.environ.get(log_env_var, "").upper()
    if SRC_LOG_LEVELS[source] not in logging.getLevelNamesMapping():
        SRC_LOG_LEVELS[source] = GLOBAL_LOG_LEVEL
    log.info(f"{log_env_var}: {SRC_LOG_LEVELS[source]}")
