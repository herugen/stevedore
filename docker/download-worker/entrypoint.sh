#!/bin/sh
set -e

if [ "$#" -eq 0 ]; then
  exec prefect worker start --pool "cobalt-downloads" --type docker
else
  exec "$@"
fi

