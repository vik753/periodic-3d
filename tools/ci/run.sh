#!/usr/bin/env bash
# Run a command and keep a copy of its output in out/logs/<name>.log.
# CI logs are not readable from the dev container, so every workflow publishes
# out/logs to the ci-results branch (see publish-results.sh).
#
# Usage: tools/ci/run.sh <name> <command> [args...]
set -uo pipefail

name="$1"
shift
mkdir -p out/logs
log="out/logs/${name}.log"
{
  echo "\$ $*"
  echo "started: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
} > "$log"
"$@" 2>&1 | tee -a "$log"
code=${PIPESTATUS[0]}
{
  echo "finished: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "exit code: ${code}"
} >> "$log"
exit "$code"
