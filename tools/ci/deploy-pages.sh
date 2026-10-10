#!/usr/bin/env bash
# Publish a static build to the gh-pages branch (GitHub Pages serves it).
# The branch holds a single commit: history of built files is not useful.
#
# Usage: tools/ci/deploy-pages.sh <dist-dir>
set -euo pipefail

dist="$1"
remote="https://x-access-token:${GITHUB_TOKEN}@github.com/${GITHUB_REPOSITORY}.git"

# GitHub Pages has no SPA fallback: serve the app for unknown paths too.
cp "$dist/index.html" "$dist/404.html"
touch "$dist/.nojekyll"

work="$(mktemp -d)"
cp -R "$dist"/. "$work"/
cd "$work"
git init --quiet -b gh-pages
git config user.name "github-actions[bot]"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
git add -A
git commit --quiet -m "deploy: ${GITHUB_SHA:-local}"
git push --quiet --force "$remote" gh-pages
echo "deploy-pages: published ${GITHUB_SHA:-local}"
