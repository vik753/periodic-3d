#!/usr/bin/env bash
# Install a Python project with a self-healing uv.lock (see npm-install.sh).
set -euo pipefail

if [ -f uv.lock ] && uv sync --locked; then
  exit 0
fi
echo "uv-sync: creating or refreshing uv.lock"
uv lock
uv sync
