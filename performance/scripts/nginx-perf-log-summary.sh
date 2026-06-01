#!/usr/bin/env bash
set -euo pipefail

SERVER_HOST="${SERVER_HOST:-}"
SSH_USER="${SSH_USER:-root}"
SSH_KEY="${SSH_KEY:-}"
PERF_LOG_PATH="${PERF_LOG_PATH:-/var/log/nginx/huairou_perf_access.log}"
SINCE_MINUTES="${SINCE_MINUTES:-30}"
TOP_N="${TOP_N:-20}"

if [ -z "${SERVER_HOST}" ]; then
  echo "ERROR: SERVER_HOST is required." >&2
  exit 1
fi

if [ -z "${SSH_KEY}" ]; then
  echo "ERROR: SSH_KEY is required." >&2
  exit 1
fi

remote_perf_log_path="$(printf "%q" "${PERF_LOG_PATH}")"
remote_since_minutes="$(printf "%q" "${SINCE_MINUTES}")"
remote_top_n="$(printf "%q" "${TOP_N}")"

ssh -i "${SSH_KEY}" -o BatchMode=yes -o StrictHostKeyChecking=accept-new "${SSH_USER}@${SERVER_HOST}" \
  "PERF_LOG_PATH=${remote_perf_log_path} SINCE_MINUTES=${remote_since_minutes} TOP_N=${remote_top_n} python3 -" <<'PY'
import math
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

path = os.environ["PERF_LOG_PATH"]
since_minutes = int(os.environ.get("SINCE_MINUTES", "30"))
top_n = int(os.environ.get("TOP_N", "20"))

if not os.path.exists(path):
    print(f"ERROR: perf log not found: {path}", file=sys.stderr)
    sys.exit(2)

if not os.path.isfile(path):
    print(f"ERROR: perf log path is not a file: {path}", file=sys.stderr)
    sys.exit(2)

cutoff = datetime.now(timezone.utc) - timedelta(minutes=since_minutes)
groups = defaultdict(lambda: {
    "request": [],
    "upstream_connect": [],
    "upstream_header": [],
    "upstream_response": [],
    "statuses": Counter(),
})
total_lines = 0
matched_lines = 0
parse_errors = 0

def parse_time(value):
    try:
        return datetime.fromisoformat(value).astimezone(timezone.utc)
    except ValueError:
        return None

def parse_nginx_time(value):
    values = []
    for item in value.replace(":", ",").split(","):
        item = item.strip()
        if not item or item == "-":
            continue
        try:
            values.append(float(item))
        except ValueError:
            continue
    if not values:
        return None
    return max(values)

def percentile(values, pct):
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, math.ceil(len(ordered) * pct) - 1)
    return ordered[min(index, len(ordered) - 1)]

def fmt_seconds(value):
    if value is None:
        return "-"
    if value >= 1:
        return f"{value:.3f}s"
    return f"{value * 1000:.1f}ms"

with open(path, "r", encoding="utf-8", errors="replace") as handle:
    for raw_line in handle:
        total_lines += 1
        line = raw_line.rstrip("\n")
        if not line:
            continue
        parts = line.split("\t")
        if len(parts) < 11:
            parse_errors += 1
            continue
        ts = parse_time(parts[0])
        if ts is None:
            parse_errors += 1
            continue
        if ts < cutoff:
            continue
        host = parts[2].strip() or "-"
        method = parts[3].strip() or "-"
        uri = (parts[4].split("?", 1)[0].strip()) or "/"
        status = parts[5].strip() or "-"
        request_time = parse_nginx_time(parts[6])
        upstream_connect_time = parse_nginx_time(parts[7])
        upstream_header_time = parse_nginx_time(parts[8])
        upstream_response_time = parse_nginx_time(parts[9])
        key = (host, method, uri)
        bucket = groups[key]
        bucket["statuses"][status] += 1
        if request_time is not None:
            bucket["request"].append(request_time)
        if upstream_connect_time is not None:
            bucket["upstream_connect"].append(upstream_connect_time)
        if upstream_header_time is not None:
            bucket["upstream_header"].append(upstream_header_time)
        if upstream_response_time is not None:
            bucket["upstream_response"].append(upstream_response_time)
        matched_lines += 1

print("== nginx performance timing summary ==")
print(f"log_path: {path}")
print(f"since_minutes: {since_minutes}")
print(f"total_lines: {total_lines}")
print(f"matched_lines: {matched_lines}")
print(f"parse_errors: {parse_errors}")

if not groups:
    print("no samples in selected window")
    sys.exit(0)

def row_metrics(item):
    _, bucket = item
    request = bucket["request"]
    return (
        percentile(request, 0.95) or 0,
        max(request) if request else 0,
        len(request),
    )

rows = sorted(groups.items(), key=row_metrics, reverse=True)

print()
print("== top endpoints by request_time p95 ==")
print("host\tmethod\turi\tcount\tstatuses\trequest_p95\trequest_p99\trequest_max\tupstream_response_p95\tupstream_response_p99\tupstream_response_max\tupstream_connect_p95\tupstream_header_p95")
for (host, method, uri), bucket in rows[:top_n]:
    statuses = ",".join(f"{status}:{count}" for status, count in sorted(bucket["statuses"].items()))
    request = bucket["request"]
    upstream_response = bucket["upstream_response"]
    upstream_connect = bucket["upstream_connect"]
    upstream_header = bucket["upstream_header"]
    print(
        "\t".join([
            host,
            method,
            uri,
            str(sum(bucket["statuses"].values())),
            statuses,
            fmt_seconds(percentile(request, 0.95)),
            fmt_seconds(percentile(request, 0.99)),
            fmt_seconds(max(request) if request else None),
            fmt_seconds(percentile(upstream_response, 0.95)),
            fmt_seconds(percentile(upstream_response, 0.99)),
            fmt_seconds(max(upstream_response) if upstream_response else None),
            fmt_seconds(percentile(upstream_connect, 0.95)),
            fmt_seconds(percentile(upstream_header, 0.95)),
        ])
    )

print()
print("== target endpoints ==")
target_paths = {
    ("huairou.tech", "GET", "/"),
    ("huairou.tech", "GET", "/api/v1/public/home"),
    ("portal-admin.huairou.tech", "GET", "/"),
    ("cg.huairou.tech", "GET", "/"),
    ("cg.huairou.tech", "GET", "/api/v1/health"),
}
for key in sorted(target_paths):
    bucket = groups.get(key)
    if not bucket:
        print("\t".join([key[0], key[1], key[2], "count=0"]))
        continue
    request = bucket["request"]
    upstream_response = bucket["upstream_response"]
    statuses = ",".join(f"{status}:{count}" for status, count in sorted(bucket["statuses"].items()))
    print(
        "\t".join([
            key[0],
            key[1],
            key[2],
            f"count={sum(bucket['statuses'].values())}",
            f"statuses={statuses}",
            f"request_p95={fmt_seconds(percentile(request, 0.95))}",
            f"request_p99={fmt_seconds(percentile(request, 0.99))}",
            f"request_max={fmt_seconds(max(request) if request else None)}",
            f"upstream_response_p95={fmt_seconds(percentile(upstream_response, 0.95))}",
            f"upstream_response_p99={fmt_seconds(percentile(upstream_response, 0.99))}",
            f"upstream_response_max={fmt_seconds(max(upstream_response) if upstream_response else None)}",
        ])
    )
PY
