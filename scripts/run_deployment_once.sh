#!/bin/sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

IMAGE="${STEVEDORE_IMAGE:-ghcr.io/herugen/stevedore/stevedore-orchestration:latest}"
ENV_FILE="${STEVEDORE_ENV_FILE:-$REPO_ROOT/profiles/local.env}"
DEPLOYMENT="${PREFECT_DEPLOYMENT:-video-to-audio-pipeline/video-pipeline}"

if [ ! -f "$ENV_FILE" ]; then
  echo "Environment file not found: $ENV_FILE" >&2
  exit 1
fi

docker run -d --rm \
  --env-file "$ENV_FILE" \
  "$IMAGE" \
  prefect deployment run "$DEPLOYMENT" "$@"


