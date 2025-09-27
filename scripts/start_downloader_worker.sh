#!/bin/sh

set -euo pipefail

IMAGE="${STEVEDORE_IMAGE:-ghcr.io/herugen/stevedore-downloader:latest}"
ENV_FILE="${STEVEDORE_ENV_FILE:-profiles/local.env}"
WORK_POOL="${WORK_POOL_NAME:-cobalt-downloads}"

if [ ! -f "$ENV_FILE" ]; then
  echo "Environment file not found: $ENV_FILE" >&2
  exit 1
fi

docker run -d --rm \
  --env-file "$ENV_FILE" \
  -v /var/run/docker.sock:/var/run/docker.sock \
  "$IMAGE" \
  prefect worker start --pool "$WORK_POOL" --type docker "$@"

