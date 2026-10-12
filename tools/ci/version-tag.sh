#!/usr/bin/env bash
# Tag the site version (apps/web/package.json, SemVer) and publish a GitHub release with its
# notes from CHANGELOG.md. Existing tags stay as they are.
#
# Usage: tools/ci/version-tag.sh [vX.Y.Z=<commit> ...]
#   The pairs tag older versions first (with --latest=false); then the current version is
#   tagged at HEAD unless it already exists. GitHub refuses GITHUB_TOKEN a tag on a commit
#   whose workflow files differ from the default branch, so older versions (1.0–1.4) stay
#   untagged; CHANGELOG links them to their commits.
# Needs GH_TOKEN with contents: write, and a full clone (fetch-depth: 0).
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"
git config user.name "github-actions[bot]"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"

notes() {
  # The section "## [X.Y.Z] — date" of CHANGELOG.md, without its heading.
  awk -v version="$1" '
    index($0, "## [" version "]") == 1 { on = 1; next }
    on && /^## \[/ { exit }
    on && /^\[/ { exit }
    on { print }
  ' CHANGELOG.md
}

tag() {
  local name="$1" commit="$2" latest="$3"
  if git ls-remote --exit-code --tags origin "refs/tags/${name}" > /dev/null 2>&1; then
    echo "version-tag: ${name} exists"
    return
  fi
  git tag -a "${name}" "${commit}" -m "Site ${name}"
  git push --quiet origin "refs/tags/${name}"
  notes "${name#v}" > "${RUNNER_TEMP:-/tmp}/notes.md"
  gh release create "${name}" --title "Site ${name}" --notes-file "${RUNNER_TEMP:-/tmp}/notes.md" \
    --verify-tag --latest="${latest}"
  echo "version-tag: ${name} → ${commit}"
}

for pair in "$@"; do
  tag "${pair%%=*}" "${pair#*=}" false
done
version="$(python3 -c 'import json; print(json.load(open("apps/web/package.json"))["version"])')"
tag "v${version}" "$(git rev-parse HEAD)" true
