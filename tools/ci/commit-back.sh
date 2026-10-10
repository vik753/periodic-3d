#!/usr/bin/env bash
# Commit files that CI generated (lockfiles) back to main.
# Pushes made with GITHUB_TOKEN do not trigger new workflow runs, so this cannot loop.
#
# Usage: tools/ci/commit-back.sh "<commit message>" <path>...
set -euo pipefail

message="$1"
shift

if [ "${GITHUB_REF:-}" != "refs/heads/main" ]; then
  echo "commit-back: not on main, skipping"
  exit 0
fi

git config user.name "github-actions[bot]"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
for path in "$@"; do
  if [ -e "$path" ]; then git add -- "$path"; fi
done
if git diff --cached --quiet; then
  echo "commit-back: nothing to commit"
  exit 0
fi
git commit --quiet -m "$message"

for attempt in 1 2 3 4 5; do
  if git push --quiet origin HEAD:main; then
    echo "commit-back: pushed"
    exit 0
  fi
  echo "commit-back: push failed (attempt ${attempt}), rebasing on main"
  git pull --quiet --rebase origin main || true
  sleep $((attempt * 3))
done
echo "commit-back: giving up" >&2
exit 1
