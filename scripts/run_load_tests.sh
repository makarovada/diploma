#!/usr/bin/env bash
# Headless-прогон Locust против запущенного DataNorma API.
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$root"

host_url="${LOAD_TEST_HOST:-http://127.0.0.1:8080}"
users="${LOAD_TEST_USERS:-10}"
spawn_rate="${LOAD_TEST_SPAWN_RATE:-2}"
run_time="${LOAD_TEST_DURATION:-1m}"
out_dir="${LOAD_TEST_OUT_DIR:-loadtest-results}"

mkdir -p "$out_dir"

echo "Locust: host=$host_url users=$users spawn_rate=$spawn_rate duration=$run_time"

locust \
  -f loadtests/locustfile.py \
  --host "$host_url" \
  --headless \
  -u "$users" \
  -r "$spawn_rate" \
  -t "$run_time" \
  --html "$out_dir/report.html" \
  --csv "$out_dir/stats" \
  "$@"

echo "Отчёт: $root/$out_dir/report.html"
