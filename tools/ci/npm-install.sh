#!/usr/bin/env bash
# Install npm dependencies with a self-healing lockfile.
# The dev container cannot reach the npm registry, so package-lock.json is
# created or refreshed here in CI and committed back by commit-back.sh.
set -euo pipefail

if [ -f package-lock.json ]; then
  if npm ci --no-audit --no-fund; then
    exit 0
  fi
  echo "npm-install: npm ci failed, refreshing package-lock.json"
fi
npm install --no-audit --no-fund
