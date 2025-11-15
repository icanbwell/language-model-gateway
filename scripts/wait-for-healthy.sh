#!/bin/sh
# wait-for-healthy.sh <container_name> [max_attempts] [interval_seconds]
# Waits for the given Docker container to report a healthy status.
# Exit codes:
#   0 - Container reported healthy
#   1 - Container unhealthy, restarting, not found, or timed out
#   2 - Usage / bad arguments
#   3 - No healthcheck defined (treated as success when NO_HEALTHCHECK_OK=1)
# Environment overrides:
#   WAIT_HEALTH_ATTEMPTS - default for max attempts (fallback 30)
#   WAIT_HEALTH_INTERVAL - default for interval seconds (fallback 2)
#   NO_HEALTHCHECK_OK    - if set to 1, exit 3 immediately when no healthcheck exists
#
# Improvements:
# - Proper quoting, structured logging with timestamps
# - Early abort on unhealthy/restarting
# - Distinguish missing healthcheck
# - Avoid echo with escape sequences; use printf
# - Optional interval seconds argument
# - Safer integer validation

set -eu

usage() {
  printf "Usage: %s <container_name> [max_attempts] [interval_seconds]\n" "$0"
}

log() {
  # Timestamped log line
  printf "[%s] %s\n" "$(date '+%Y-%m-%dT%H:%M:%S')" "$*"
}

log_progress() {
  # Log on same line with carriage return (no newline)
  printf "\r[%s] %s" "$(date '+%Y-%m-%dT%H:%M:%S')" "$*"
}

if [ "$#" -lt 1 ]; then
  usage
  exit 2
fi

CONTAINER_NAME="$1"
MAX_ATTEMPTS="${2:-${WAIT_HEALTH_ATTEMPTS:-30}}"
INTERVAL="${3:-${WAIT_HEALTH_INTERVAL:-2}}"
NO_HEALTHCHECK_OK="${NO_HEALTHCHECK_OK:-0}"

# Validate integers (basic check: all digits)
case "$MAX_ATTEMPTS" in
  ''|*[!0-9]*) log "ERROR: max_attempts must be a positive integer"; usage; exit 2 ;;
  *) : ;;
esac
case "$INTERVAL" in
  ''|*[!0-9]*) log "ERROR: interval_seconds must be a positive integer"; usage; exit 2 ;;
  *) : ;;
esac

ATTEMPT=0
log "Waiting for container '$CONTAINER_NAME' to become healthy (max_attempts=$MAX_ATTEMPTS interval=${INTERVAL}s)"

# Trap Ctrl-C
trap 'log "Interrupted"; exit 1' INT

# Function to retrieve status/state
get_status() {
  # We attempt to read both health status and container state.
  STATUS="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{end}}' "$CONTAINER_NAME" 2>/dev/null || true)"
  STATE="$(docker inspect --format '{{.State.Status}}' "$CONTAINER_NAME" 2>/dev/null || true)"
  # If docker inspect failed (container missing)
  if [ -z "$STATE" ]; then
    STATE="not-found"
  fi
  if [ -z "$STATUS" ]; then
    STATUS="no-healthcheck" # Distinguish missing healthcheck
  fi
}

while [ "$ATTEMPT" -lt "$MAX_ATTEMPTS" ]; do
  ATTEMPT=$((ATTEMPT + 1))
  get_status
  log_progress "Attempt $ATTEMPT/$MAX_ATTEMPTS HEALTH=$STATUS STATE=$STATE"

  case "$STATUS" in
    healthy)
      printf "\n" # Move to new line before final message
      log "Container '$CONTAINER_NAME' is healthy."
      exit 0
      ;;
    starting)
      : # keep waiting
      ;;
    unhealthy)
      printf "\n" # Move to new line before error message
      log "ERROR: Container '$CONTAINER_NAME' reported unhealthy. Showing diagnostics."
      docker ps --filter "name=$CONTAINER_NAME" --format 'table {{.Names}}\t{{.Status}}'
      docker logs "$CONTAINER_NAME" 2>&1 | tail -n 100 || true
      exit 1
      ;;
    no-healthcheck)
      if [ "$NO_HEALTHCHECK_OK" = "1" ]; then
        printf "\n" # Move to new line before message
        log "No healthcheck defined for '$CONTAINER_NAME' (treating as success)."
        exit 3
      else
        printf "\n" # Move to new line before warning
        log "WARNING: No healthcheck defined for '$CONTAINER_NAME'; continuing to wait on running state."
      fi
      ;;
  esac

  case "$STATE" in
    restarting|dead|exited)
      printf "\n" # Move to new line before error message
      log "ERROR: Container state is '$STATE'. Showing diagnostics."
      docker ps --filter "name=$CONTAINER_NAME" --format 'table {{.Names}}\t{{.Status}}'
      docker logs "$CONTAINER_NAME" 2>&1 | tail -n 100 || true
      exit 1
      ;;
    not-found)
      : # keep waiting
      ;;
  esac

  sleep "$INTERVAL"
done

printf "\n" # Move to new line before final error message
log "ERROR: Container '$CONTAINER_NAME' did not become healthy within $MAX_ATTEMPTS attempts (interval=${INTERVAL}s)"
docker ps --filter "name=$CONTAINER_NAME" --format 'table {{.Names}}\t{{.Status}}'
docker logs "$CONTAINER_NAME" 2>&1 | tail -n 100 || true
exit 1
