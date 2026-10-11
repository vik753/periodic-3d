#!/usr/bin/env bash
# Fetch the "How to use" videos (workflow guide), if the site has them.
#
# The pointer lives in data/GUIDE (one line):
#   release:<tag>   GitHub release with guide-<lang>.mp4, guide-<lang>.jpg, manifest.json
#   none            no video: the About panel hides the button
# Without the file there is no video.
#
# Usage: tools/ci/fetch-guide.sh <out-dir>   → <out-dir>/manifest.json and the files
# Needs GH_TOKEN.
set -euo pipefail

mkdir -p "$1"
out="$(cd "$1" && pwd)"
cd "$(git rev-parse --show-toplevel)"

pointer="none"
if [ -f data/GUIDE ]; then
  pointer="$(tr -d '[:space:]' < data/GUIDE)"
fi

case "$pointer" in
  none)
    echo "fetch-guide: no guide video (data/GUIDE)"
    rmdir "$out" 2>/dev/null || true
    exit 0
    ;;
  release:*)
    tag="${pointer#release:}"
    gh release download "$tag" --dir "$out" --clobber \
      --pattern 'guide-*.mp4' --pattern 'guide-*.jpg' --pattern 'manifest.json'
    ls -la "$out"
    ;;
  *)
    echo "fetch-guide: unknown pointer '${pointer}'" >&2
    exit 1
    ;;
esac
