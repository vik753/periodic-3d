#!/usr/bin/env bash
# Publish CI outputs (reports, screenshots, previews) to the `ci-results` branch.
#
# Usage: tools/ci/publish-results.sh <source-path> <dest-dir> [commit-message]
#   <source-path>  file or directory to copy
#   <dest-dir>     directory inside the ci-results branch (replaced on each publish)
#
# Requires GITHUB_TOKEN and GITHUB_REPOSITORY in the environment
# and `permissions: contents: write` in the workflow.
set -euo pipefail

src="$1"
dest="$2"
msg="${3:-ci: publish ${dest}}"
branch="ci-results"
remote="https://x-access-token:${GITHUB_TOKEN}@github.com/${GITHUB_REPOSITORY}.git"

work="$(mktemp -d)"
if git ls-remote --exit-code --heads "$remote" "$branch" >/dev/null 2>&1; then
  git clone --quiet --depth 1 --branch "$branch" "$remote" "$work"
else
  git init --quiet -b "$branch" "$work"
  git -C "$work" remote add origin "$remote"
  echo "# CI results (machine generated)" > "$work/README.md"
fi

git -C "$work" config user.name "github-actions[bot]"
git -C "$work" config user.email "41898282+github-actions[bot]@users.noreply.github.com"

rm -rf "${work:?}/${dest}"
mkdir -p "$work/$dest"
if [ -d "$src" ]; then
  cp -R "$src"/. "$work/$dest/"
else
  cp "$src" "$work/$dest/"
fi

cat > "$work/$dest/_meta.json" <<EOF
{"sha": "${GITHUB_SHA:-unknown}", "run_id": "${GITHUB_RUN_ID:-unknown}", "ref": "${GITHUB_REF:-unknown}", "time_utc": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"}
EOF

cd "$work"
git add -A
if git diff --cached --quiet; then
  echo "publish-results: nothing to commit"
  exit 0
fi
git commit --quiet -m "$msg"

for attempt in 1 2 3 4 5; do
  if git push --quiet origin "HEAD:${branch}"; then
    echo "publish-results: pushed ${dest} to ${branch}"
    exit 0
  fi
  echo "publish-results: push failed (attempt ${attempt}), rebasing"
  git pull --quiet --rebase origin "$branch" || true
  sleep $((attempt * 3))
done
echo "publish-results: giving up" >&2
exit 1
