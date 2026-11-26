#!/usr/bin/env bash
# Install pstack into DeepSeek Harness. Safe to rerun: it pulls the latest port.
set -euo pipefail

REPO_URL="${PSTACK_DSH_REPO:-https://github.com/haroon0x/pstack-dsh}"
DSH_DIR="${DSH_HOME:-$HOME/.dsh}"
TARGET="${PSTACK_DSH_DIR:-$DSH_DIR/vendor/pstack-dsh}"

for tool in git python3; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "error: $tool is required" >&2
    exit 1
  fi
done

if [[ -d "$TARGET/.git" ]]; then
  echo "updating $TARGET"
  git -C "$TARGET" pull --ff-only
else
  if [[ -e "$TARGET" && -n "$(ls -A "$TARGET" 2>/dev/null)" ]]; then
    echo "error: $TARGET exists and is not a git checkout." >&2
    echo "Move it aside or set PSTACK_DSH_DIR to another path, then run this script again." >&2
    exit 1
  fi
  echo "cloning $REPO_URL to $TARGET"
  mkdir -p "$(dirname "$TARGET")"
  git clone --depth 1 "$REPO_URL" "$TARGET"
fi

exec python3 "$TARGET/install.py" install
