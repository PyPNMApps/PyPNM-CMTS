# FILE: tools/smoke/lib/smoke-lib.sh
#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

set -euo pipefail
IFS=$'\n\t'

SMOKE_CURL_TIMEOUT_SECONDS="${SMOKE_CURL_TIMEOUT_SECONDS:-5}"
SMOKE_STARTUP_TIMEOUT_SECONDS="${SMOKE_STARTUP_TIMEOUT_SECONDS:-20}"
SMOKE_STARTUP_POLL_SECONDS="${SMOKE_STARTUP_POLL_SECONDS:-0.25}"

smoke_info() {
  printf "%s\n" "$*"
}

smoke_warn() {
  printf "WARN: %s\n" "$*" >&2
}

smoke_err() {
  printf "ERROR: %s\n" "$*" >&2
}

smoke_die() {
  smoke_err "$*"
  exit 1
}

smoke_require_cmd() {
  local cmd="$1"
  command -v "$cmd" >/dev/null 2>&1 || smoke_die "Missing required command: $cmd"
}

smoke_mktemp_dir() {
  mktemp -d 2>/dev/null || mktemp -d -t pypnm_cmts_smoke
}

smoke_http_get() {
  local url="$1"
  local body_path="$2"
  local err_path="$3"

  : >"$body_path"
  : >"$err_path"

  local code=""
  local rc=0
  code="$(curl \
    --max-time "${SMOKE_CURL_TIMEOUT_SECONDS}" \
    --silent --show-error \
    --location \
    --output "$body_path" \
    --write-out "%{http_code}" \
    "$url" 2>"$err_path")" || rc=$?

  if (( rc != 0 )); then
    printf "000"
    return 0
  fi

  if [[ -z "$code" ]]; then
    printf "000"
    return 0
  fi

  printf "%s" "$code"
}

smoke_json_get() {
  local body_path="$1"
  local dotted_path="$2"

  python - "$body_path" "$dotted_path" <<'PY'
import json
import sys

body_path = sys.argv[1]
dotted_path = sys.argv[2]

try:
    text = open(body_path, "r", encoding="utf-8").read()
except Exception:
    sys.exit(0)

if not text.strip():
    sys.exit(0)

try:
    data = json.loads(text)
except Exception:
    sys.exit(0)

value = data
for part in dotted_path.split("."):
    if isinstance(value, dict) and part in value:
        value = value[part]
    else:
        sys.exit(0)

if value is None:
    sys.exit(0)

if isinstance(value, (dict, list)):
    print(json.dumps(value))
else:
    print(value)
PY
}

smoke_assert_http_code() {
  local code="$1"
  local expected="$2"
  local url="$3"
  local body_path="$4"
  local err_path="$5"

  if [[ "$code" != "$expected" ]]; then
    smoke_err "HTTP $url: expected $expected, got $code"
    if [[ -s "$err_path" ]]; then
      smoke_err "curl stderr:"
      sed -e 's/^/  /' "$err_path" >&2 || true
    fi
    if [[ -s "$body_path" ]]; then
      smoke_err "response body:"
      sed -e 's/^/  /' "$body_path" >&2 || true
    else
      smoke_err "response body: <empty>"
    fi
    exit 1
  fi
}

smoke_assert_json_equals() {
  local body_path="$1"
  local dotted_path="$2"
  local expected="$3"
  local label="$4"

  local actual=""
  actual="$(smoke_json_get "$body_path" "$dotted_path" || true)"
  if [[ "$actual" != "$expected" ]]; then
    smoke_err "$label: expected '$expected', got '$actual'"
    smoke_err "response body:"
    sed -e 's/^/  /' "$body_path" >&2 || true
    exit 1
  fi
}

smoke_wait_for_url_ok() {
  local url="$1"
  local timeout_seconds="$2"

  local tmp_dir
  tmp_dir="$(smoke_mktemp_dir)"
  local body_path="$tmp_dir/body"
  local err_path="$tmp_dir/err"

  local start
  start="$(python - <<'PY'
import time
print(time.time())
PY
)"

  while true; do
    local code
    code="$(smoke_http_get "$url" "$body_path" "$err_path")"
    if [[ "$code" == "200" ]]; then
      rm -rf "$tmp_dir" || true
      return 0
    fi

    local now elapsed
    now="$(python - <<'PY'
import time
print(time.time())
PY
)"
    elapsed="$(python - "$start" "$now" <<'PY'
import sys
start = float(sys.argv[1])
now = float(sys.argv[2])
print(now - start)
PY
)"
    if python - "$elapsed" "$timeout_seconds" <<'PY'
import sys
elapsed = float(sys.argv[1])
timeout = float(sys.argv[2])
raise SystemExit(0 if elapsed >= timeout else 1)
PY
    then
      smoke_err "Timed out waiting for 200 OK: $url"
      if [[ -s "$err_path" ]]; then
        smoke_err "curl stderr:"
        sed -e 's/^/  /' "$err_path" >&2 || true
      fi
      if [[ -s "$body_path" ]]; then
        smoke_err "response body:"
        sed -e 's/^/  /' "$body_path" >&2 || true
      fi
      rm -rf "$tmp_dir" || true
      return 1
    fi

    python - "$SMOKE_STARTUP_POLL_SECONDS" <<'PY'
import sys, time
time.sleep(float(sys.argv[1]))
PY
  done
}

smoke_backup_dir() {
  local src_dir="$1"
  local dst_dir="$2"

  if [[ -d "$src_dir" ]]; then
    mkdir -p "$(dirname "$dst_dir")"
    mv "$src_dir" "$dst_dir"
    return 0
  fi
  return 1
}

smoke_restore_dir() {
  local src_dir="$1"
  local dst_dir="$2"

  if [[ -d "$src_dir" ]]; then
    rm -rf "$dst_dir" || true
    mkdir -p "$(dirname "$dst_dir")"
    mv "$src_dir" "$dst_dir"
  fi
}
