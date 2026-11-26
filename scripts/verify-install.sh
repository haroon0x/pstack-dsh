#!/usr/bin/env bash
# Install the port into a scratch DSH home at https://github.com/haroon0x/pstack-dsh
# current upstream and verify the result. This is the CI check and the local
# pre-push check.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRATCH="$(mktemp -d)"
trap 'rm -rf "$SCRATCH"' EXIT

mkdir -p "$SCRATCH/vendor"
cp -R "$ROOT" "$SCRATCH/vendor/pstack-dsh"
rm -rf "$SCRATCH/vendor/pstack-dsh/.git"
rm -f "$SCRATCH/vendor/pstack-dsh/manifest.json"

export DSH_HOME="$SCRATCH"
python3 "$SCRATCH/vendor/pstack-dsh/install.py" install "$@"
python3 "$SCRATCH/vendor/pstack-dsh/install.py" check
