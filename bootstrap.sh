#!/bin/sh
# SPDX-License-Identifier: Apache-2.0
# This URL becomes usable only after the repository has been published.
set -eu
paperdock_ref=main
if [ "${1:-}" = --ref ]; then
    [ "$#" -ge 2 ] || { echo 'Usage: bootstrap.sh [--ref REF] [installer options]' >&2; exit 2; }
    paperdock_ref=$2
    shift 2
fi
case "$paperdock_ref" in ''|-*|*[!a-zA-Z0-9._/-]*) echo 'Invalid Git ref' >&2; exit 2;; esac
for paperdock_argument in "$@"; do
    if [ "$paperdock_argument" = --dry-run ]; then
        echo "After publication: clone https://github.com/designshot/paperdock at $paperdock_ref and run install.sh. No actions performed."
        exit 0
    fi
done
[ "$(id -u)" != 0 ] || { echo 'Run as your normal user, not with sudo.' >&2; exit 1; }
[ -r /etc/os-release ] || { echo 'Unsupported system: /etc/os-release missing.' >&2; exit 1; }
. /etc/os-release
case "${ID:-}:${VERSION_ID:-}" in
    ubuntu:24.04|pop:24.04|debian:12|debian:12.*|debian:13|debian:13.*) ;;
    *) echo 'Supported: Ubuntu/Pop!_OS 24.04 and Debian 12/13.' >&2; exit 1;;
esac
if ! command -v git >/dev/null 2>&1; then
    command -v sudo >/dev/null 2>&1 || { echo 'Git is missing; install it first.' >&2; exit 1; }
    sudo apt-get update
    sudo apt-get install -y git ca-certificates
fi
paperdock_temporary=$(mktemp -d)
trap 'rm -rf -- "$paperdock_temporary"' EXIT HUP INT TERM
git clone --depth 1 --branch "$paperdock_ref" -- https://github.com/designshot/paperdock.git "$paperdock_temporary/source"
bash "$paperdock_temporary/source/install.sh" "$@"
