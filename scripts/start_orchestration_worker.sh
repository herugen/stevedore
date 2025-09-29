#!/bin/sh

set -euo pipefail

IMAGE="${STEVEDORE_ORCHESTRATION_IMAGE:-ghcr.io/herugen/stevedore/stevedore-orchestration:latest}"
ENV_FILE="${STEVEDORE_ORCHESTRATION_ENV_FILE:-profiles/local.env}"
WORK_POOL="${ORCHESTRATION_WORK_POOL_NAME:-orchestration}"

if [ ! -f "$ENV_FILE" ]; then
  echo "Environment file not found: $ENV_FILE" >&2
  exit 1
fi

docker run -d --rm \
  --env-file "$ENV_FILE" \
  -v /var/run/docker.sock:/var/run/docker.sock \
  "$IMAGE" \
  prefect worker start --pool "$WORK_POOL" --type docker "$@"


