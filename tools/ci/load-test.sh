#!/usr/bin/env bash
# Small HTTP load test: every URL is requested <rounds> times with 32 parallel
# connections; prints count, errors, requests per second and latency percentiles.
#
# Usage: tools/ci/load-test.sh <rounds> <url> [<url> ...]
set -euo pipefail

rounds="$1"
shift
work="$(mktemp -d)"
for _ in $(seq 1 "$rounds"); do printf '%s\n' "$@"; done > "$work/urls.txt"
start=$(date +%s.%N)
xargs -P 32 -n 1 curl -s -o /dev/null -w '%{http_code} %{time_total}\n' < "$work/urls.txt" > "$work/times.txt"
end=$(date +%s.%N)
python3 - "$start" "$end" "$work/times.txt" <<'PY'
import statistics
import sys

rows = [line.split() for line in open(sys.argv[3])]
times = sorted(float(t) * 1000 for _, t in rows)
errors = sum(1 for code, _ in rows if code != "200")
q = statistics.quantiles(times, n=100)
seconds = float(sys.argv[2]) - float(sys.argv[1])
print(f"requests: {len(rows)}, errors: {errors}, concurrency: 32, rps: {len(rows) / seconds:.0f}")
print(f"latency ms: p50 {q[49]:.1f}, p95 {q[94]:.1f}, p99 {q[98]:.1f}, max {times[-1]:.1f}")
PY
