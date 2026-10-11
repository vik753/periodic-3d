#!/usr/bin/env bash
# Put the generated space music (tools/guide/music.py) under a guide video.
# The music is as long as the video; a video that already has sound is copied as is.
#
# Usage: tools/ci/guide-music.sh <in.mp4> <out.mp4>
# Needs ffmpeg and python3 with numpy and scipy.
set -euo pipefail

in="$1"
out="$2"
here="$(cd "$(dirname "$0")" && pwd)"

if [ -n "$(ffprobe -v error -select_streams a -show_entries stream=index -of csv=p=0 "$in")" ]; then
  echo "guide-music: $in already has sound"
  [ "$in" = "$out" ] || cp "$in" "$out"
  exit 0
fi

seconds="$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$in")"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
python3 "$here/../guide/music.py" "$seconds" "$tmp/music.wav"
ffmpeg -hide_banner -loglevel warning -y -i "$in" -i "$tmp/music.wav" \
  -map 0:v:0 -map 1:a:0 -c:v copy -c:a aac -b:a 160k -shortest -movflags +faststart "$tmp/out.mp4"
mv "$tmp/out.mp4" "$out"
echo "guide-music: $out ($seconds s)"
