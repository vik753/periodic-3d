#!/usr/bin/env bash
# Small HTTP load test: every URL is requested <rounds> times with $CONCURRENCY
# parallel connections (default 32); prints count, errors, requests per second and
# latency percentiles. PER_URL=1 measures each URL on its own as well.
#
# Usage: [CONCURRENCY=32] [PER_URL=1] tools/ci/load-test.sh <rounds> <url> [<url> ...]
set -euo pipefail

rounds="$1"
shift
concurrency="${CONCURRENCY:-32}"
work="$(mktemp -d)"

run() {  # <label> <url>...
  local label="$1"
  shift
  for _ in $(seq 1 "$rounds"); do printf '%s\n' "$@"; done > "$work/urls.txt"
  local start end
  start=$(date +%s.%N)
  xargs -P "$concurrency" -n 1 curl -s -o /dev/null -w '%{http_code} %{time_total}\n' < "$work/urls.txt" > "$work/times.txt"
  end=$(date +%s.%N)
  python3 - "$start" "$end" "$work/times.txt" "$label" "$concurrency" <<'PY'
import statistics
import sys

rows = [line.split() for line in open(sys.argv[3])]
times = sorted(float(t) * 1000 for _, t in rows)
errors = sum(1 for code, _ in rows if code != "200")
q = statistics.quantiles(times, n=100)
seconds = float(sys.argv[2]) - float(sys.argv[1])
print(
    f"{sys.argv[4]}: requests {len(rows)}, errors {errors}, concurrency {sys.argv[5]}, "
    f"rps {len(rows) / seconds:.0f}, ms p50 {q[49]:.1f} p95 {q[94]:.1f} p99 {q[98]:.1f} max {times[-1]:.1f}"
)
PY
}

run "all" "$@"
if [ "${PER_URL:-0}" = "1" ]; then
  for url in "$@"; do run "${url#*/api/v1}" "$url"; done
fi
