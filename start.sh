#!/bin/sh
set -eu
cd "$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
exec "${PAPERDOCK_PYTHON:-python3}" -m paperdock --desktop "$@"
