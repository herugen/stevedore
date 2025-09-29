#!/bin/sh
set -e

DEFAULT_POOL="audio-processing"
DEFAULT_TYPE="docker"

if [ "$#" -eq 0 ]; then
  exec prefect worker start --pool "${WORK_POOL:-$DEFAULT_POOL}" --type "${WORK_POOL_TYPE:-$DEFAULT_TYPE}"
else
  exec "$@"
fi


