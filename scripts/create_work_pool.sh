#!/bin/sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

IMAGE="${STEVEDORE_IMAGE:-ghcr.io/herugen/stevedore-downloader:latest}"
POOL_NAME="${WORK_POOL_NAME:-cobalt-downloads}"
POOL_TYPE="${WORK_POOL_TYPE:-docker}"
ENV_FILE="${STEVEDORE_ENV_FILE:-$REPO_ROOT/profiles/local.env}"

if [ ! -f "$ENV_FILE" ]; then
  echo "Environment file not found: $ENV_FILE" >&2
  exit 1
fi

docker run --rm \
  --env-file "$ENV_FILE" \
  "$IMAGE" \
  stevedore create-work-pool "$POOL_NAME" --type "$POOL_TYPE" "$@"

