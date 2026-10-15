#!/bin/sh
# SPDX-License-Identifier: Apache-2.0
set -eu
paperdock_source=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
paperdock_python=${PAPERDOCK_INSTALL_PYTHON:-python3}
if ! command -v "$paperdock_python" >/dev/null 2>&1; then
    [ -z "${PAPERDOCK_INSTALL_PYTHON:-}" ] || { echo 'Configured Python interpreter was not found.' >&2; exit 1; }
    for paperdock_argument in "$@"; do
        case "$paperdock_argument" in
            --dry-run|--skip-system-packages|--offline)
                echo 'Python 3 is required to inspect/install with these options; no changes performed.' >&2
                exit 1;;
        esac
    done
    [ "$(id -u)" != 0 ] || { echo 'Run as your normal user, not with sudo.' >&2; exit 1; }
    [ -r /etc/os-release ] || { echo 'Unsupported system: /etc/os-release missing.' >&2; exit 1; }
    . /etc/os-release
    case "${ID:-}:${VERSION_ID:-}" in
        ubuntu:24.04|pop:24.04|debian:12|debian:12.*|debian:13|debian:13.*) ;;
        *) echo 'Supported: Ubuntu/Pop!_OS 24.04 and Debian 12/13.' >&2; exit 1;;
    esac
    command -v sudo >/dev/null 2>&1 || { echo 'sudo is missing; ask your administrator to install Python 3.' >&2; exit 1; }
    sudo apt-get update
    sudo apt-get install -y python3 python3-venv
fi
exec "$paperdock_python" "$paperdock_source/scripts/install.py" "$@"
