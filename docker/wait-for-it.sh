#!/bin/sh
# wait-for-it.sh — wait for TCP service to be ready
set -e

HOST="$1"
PORT="$2"
TIMEOUT="${3:-30}"
INTERVAL="${4:-2}"

shift 2 || true

echo "Waiting for $HOST:$PORT (timeout: ${TIMEOUT}s)..."
start=$(date +%s)
while true; do
  if nc -z "$HOST" "$PORT" 2>/dev/null; then
    echo "$HOST:$PORT is ready"
    exec "$@"
    exit 0
  fi
  now=$(date +%s)
  elapsed=$((now - start))
  if [ "$elapsed" -ge "$TIMEOUT" ]; then
    echo "Timeout waiting for $HOST:$PORT"
    exit 1
  fi
  sleep "$INTERVAL"
done
