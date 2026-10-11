#!/usr/bin/env bash
# Fetch the GNoME layer of predicted materials (ADR 0007), if the site uses one.
#
# The pointer lives in data/GNOME (one line):
#   release:<tag>       GitHub release asset gnome-*.tar.gz (full layer)
#   ci-results:<dir>    <dir>/gnome.tar.gz on the ci-results branch (quick builds)
#   none                no layer: the site shows known compounds only
# Without the file there is no layer.
#
# Usage: tools/ci/fetch-gnome.sh <out-dir>   → <out-dir>/gnome.tar.gz, or nothing
# Needs GH_TOKEN for releases.
set -euo pipefail

mkdir -p "$1"
out="$(cd "$1" && pwd)"
cd "$(git rev-parse --show-toplevel)"

pointer="none"
if [ -f data/GNOME ]; then
  pointer="$(tr -d '[:space:]' < data/GNOME)"
fi

case "$pointer" in
  none)
    echo "fetch-gnome: no GNoME layer (data/GNOME)"
    exit 0
    ;;
  release:*)
    tag="${pointer#release:}"
    gh release download "$tag" --pattern 'gnome-*.tar.gz' --output "$out/gnome.tar.gz" --clobber
    ;;
  ci-results:*)
    dir="${pointer#ci-results:}"
    git fetch --quiet --depth 1 origin "+refs/heads/ci-results:refs/remotes/origin/ci-results"
    git show "origin/ci-results:${dir}/gnome.tar.gz" > "$out/gnome.tar.gz"
    ;;
  *)
    echo "fetch-gnome: unknown pointer '${pointer}'" >&2
    exit 1
    ;;
esac

echo "fetch-gnome: ${pointer} → ${out}/gnome.tar.gz ($(stat -c %s "$out/gnome.tar.gz") bytes)"
echo "$pointer" > "$out/POINTER"
