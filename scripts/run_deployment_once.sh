#!/bin/sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

IMAGE="${STEVEDORE_IMAGE:-ghcr.io/herugen/stevedore/stevedore-downloader:latest}"
ENV_FILE="${STEVEDORE_ENV_FILE:-$REPO_ROOT/profiles/local.env}"
DEPLOYMENT="${PREFECT_DEPLOYMENT:-cobalt-video-download/cobalt-download-worker}"

if [ ! -f "$ENV_FILE" ]; then
  echo "Environment file not found: $ENV_FILE" >&2
  exit 1
fi

docker run -d --rm \
  --env-file "$ENV_FILE" \
  "$IMAGE" \
  prefect deployment run "$DEPLOYMENT" "$@"


