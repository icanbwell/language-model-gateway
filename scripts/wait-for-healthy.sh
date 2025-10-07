#!/bin/sh
# Usage: wait-for-healthy.sh <container_name> [max_attempts]
# Waits for the given Docker container to become healthy.

CONTAINER_NAME="$1"
MAX_ATTEMPTS="${2:-30}"
ATTEMPT=0

if [ -z "$CONTAINER_NAME" ]; then
  echo "Usage: $0 <container_name> [max_attempts]"
  exit 2
fi

printf "Waiting for $CONTAINER_NAME to become healthy..."
while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
  STATUS=$(docker inspect --format '{{.State.Health.Status}}' "$CONTAINER_NAME" 2>/dev/null)
  STATE=$(docker inspect --format '{{.State.Status}}' "$CONTAINER_NAME" 2>/dev/null)
  if [ "$STATUS" = "healthy" ]; then
    echo "\n$CONTAINER_NAME is healthy."
    exit 0
  elif [ "$STATUS" = "unhealthy" ] || [ "$STATE" = "restarting" ]; then
    echo "\n========== ERROR: $CONTAINER_NAME is unhealthy or restarting =========="
    docker ps
    docker logs "$CONTAINER_NAME"
    exit 1
  fi
  printf "."
  sleep 2
  ATTEMPT=$((ATTEMPT + 1))
done

echo "\n========== ERROR: $CONTAINER_NAME did not become healthy within timeout =========="
docker ps
docker logs "$CONTAINER_NAME"
exit 1

