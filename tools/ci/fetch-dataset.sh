#!/usr/bin/env bash
# Fetch the dataset that the site and the API are built from.
#
# The pointer lives in data/DATASET (one line):
#   release:<tag>       GitHub release asset dataset-*.tar.gz (full datasets)
#   ci-results:<dir>    <dir>/dataset.tar.gz on the ci-results branch (small slices)
# Without the file the latest slice is used: ci-results:data/latest.
#
# Usage: tools/ci/fetch-dataset.sh <out-dir>   → <out-dir>/dataset.tar.gz
# Needs GH_TOKEN for releases.
set -euo pipefail

mkdir -p "$1"
out="$(cd "$1" && pwd)"
cd "$(git rev-parse --show-toplevel)"

pointer="ci-results:data/latest"
if [ -f data/DATASET ]; then
  pointer="$(tr -d '[:space:]' < data/DATASET)"
fi

case "$pointer" in
  release:*)
    tag="${pointer#release:}"
    gh release download "$tag" --pattern 'dataset-*.tar.gz' --output "$out/dataset.tar.gz" --clobber
    ;;
  ci-results:*)
    dir="${pointer#ci-results:}"
    git fetch --quiet --depth 1 origin "+refs/heads/ci-results:refs/remotes/origin/ci-results"
    git show "origin/ci-results:${dir}/dataset.tar.gz" > "$out/dataset.tar.gz"
    ;;
  *)
    echo "fetch-dataset: unknown pointer '${pointer}'" >&2
    exit 1
    ;;
esac

echo "fetch-dataset: ${pointer} → ${out}/dataset.tar.gz ($(stat -c %s "$out/dataset.tar.gz") bytes)"
echo "$pointer" > "$out/POINTER"
