# FILE: tools/smoke-test-operational.sh
#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia
#
# Smoke test the /ops operational endpoints end-to-end (router wiring + runtime behavior).
#
# Usage:
#   chmod +x tools/smoke-test-operational.sh
#   ./tools/smoke-test-operational.sh
#
# Optional env overrides:
#   PORT=8801 HOST=127.0.0.1 LOG_LEVEL=warning ./tools/smoke-test-operational.sh

set -euo pipefail
IFS=$'\n\t'

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8801}"
LOG_LEVEL="${LOG_LEVEL:-warning}"
BASE_URL="http://${HOST}:${PORT}"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG_DIR="${REPO_ROOT}/config"
CONFIG_PATH="${CONFIG_DIR}/system.json"

SMOKE_ROOT="$(mktemp -d)"
SMOKE_CONFIG="${SMOKE_ROOT}/system.json"
SMOKE_STATE_DIR_BASE="${SMOKE_ROOT}/state"
SERVER_PID=""
FAKE_PIDS=()

cleanup() {
  if [[ -n "${SERVER_PID}" ]]; then
    kill "${SERVER_PID}" >/dev/null 2>&1 || true
    wait "${SERVER_PID}" >/dev/null 2>&1 || true
    SERVER_PID=""
  fi

  for pid in "${FAKE_PIDS[@]:-}"; do
    kill "${pid}" >/dev/null 2>&1 || true
    wait "${pid}" >/dev/null 2>&1 || true
  done

  if [[ -f "${SMOKE_ROOT}/system.json.bak" ]]; then
    mkdir -p "${CONFIG_DIR}"
    mv -f "${SMOKE_ROOT}/system.json.bak" "${CONFIG_PATH}" >/dev/null 2>&1 || true
  else
    if [[ -f "${SMOKE_ROOT}/system.json.prev" ]]; then
      mkdir -p "${CONFIG_DIR}"
      mv -f "${SMOKE_ROOT}/system.json.prev" "${CONFIG_PATH}" >/dev/null 2>&1 || true
    fi
  fi

  rm -rf "${SMOKE_ROOT}" >/dev/null 2>&1 || true
}
trap cleanup EXIT

die() {
  echo "ERROR: $*" 1>&2
  exit 1
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "Missing required command: $1"
}

json_get() {
  local key="$1"
  python - "$key" <<'PY'
import json, sys
key = sys.argv[1]
doc = json.loads(sys.stdin.read())
parts = key.split(".")
cur = doc
for p in parts:
    if p == "":
        continue
    if isinstance(cur, dict) and p in cur:
        cur = cur[p]
    else:
        print("")
        raise SystemExit(0)
if cur is None:
    print("null")
elif isinstance(cur, (dict, list)):
    print(json.dumps(cur))
else:
    print(str(cur))
PY
}

curl_json() {
  local path="$1"
  local expected_code="$2"

  local out
  out="$(curl -sS -w '\n%{http_code}' "${BASE_URL}${path}" || true)"
  local body code
  body="$(printf '%s' "${out}" | sed '$d')"
  code="$(printf '%s' "${out}" | tail -n 1)"

  if [[ "${code}" != "${expected_code}" ]]; then
    echo "---- ${path} (expected HTTP ${expected_code}, got HTTP ${code}) ----" 1>&2
    echo "${body}" 1>&2
    die "Unexpected HTTP status for ${path}"
  fi

  printf '%s' "${body}"
}

assert_eq() {
  local label="$1"
  local got="$2"
  local expected="$3"
  if [[ "${got}" != "${expected}" ]]; then
    die "${label}: expected '${expected}', got '${got}'"
  fi
}

assert_non_empty() {
  local label="$1"
  local got="$2"
  if [[ -z "${got}" || "${got}" == "null" ]]; then
    die "${label}: expected non-empty value"
  fi
}

detect_uvicorn_app() {
  python - <<'PY'
import importlib, sys

candidates = [
    "pypnm_cmts.api.main:app",
    "pypnm_cmts.api.app:app",
    "pypnm_cmts.api.server:app",
    "pypnm_cmts.api.api:app",
    "pypnm_cmts.api.router:app",
    "pypnm_cmts.main:app",
]

for item in candidates:
    mod_name, _, attr = item.partition(":")
    try:
        mod = importlib.import_module(mod_name)
    except Exception:
        continue
    if hasattr(mod, attr):
        print(item)
        raise SystemExit(0)

print("")
raise SystemExit(0)
PY
}

write_system_json() {
  local mode="$1"
  local state_dir="$2"
  local election_name="$3"
  local include_sg="$4"
  local sg_enabled="$5"

  mkdir -p "$(dirname "${SMOKE_CONFIG}")"

  if [[ "${include_sg}" == "true" ]]; then
    cat > "${SMOKE_CONFIG}" <<EOF
{
  "CmtsOrchestrator": {
    "mode": "${mode}",
    "state_dir": "${state_dir}",
    "election_name": "${election_name}",
    "default_tests": ["ds_ofdm_rxmer"],
    "service_groups": [
      { "sg_id": 7, "name": "sg-7", "cmts_index": 0, "enabled": ${sg_enabled} }
    ]
  }
}
EOF
  else
    cat > "${SMOKE_CONFIG}" <<EOF
{
  "CmtsOrchestrator": {
    "mode": "${mode}",
    "state_dir": "${state_dir}",
    "election_name": "${election_name}",
    "default_tests": ["ds_ofdm_rxmer"],
    "service_groups": []
  }
}
EOF
  fi
}

swap_in_config() {
  mkdir -p "${CONFIG_DIR}"

  if [[ -f "${CONFIG_PATH}" ]]; then
    mv -f "${CONFIG_PATH}" "${SMOKE_ROOT}/system.json.prev"
  fi
  cp -f "${SMOKE_CONFIG}" "${CONFIG_PATH}"
  cp -f "${SMOKE_CONFIG}" "${SMOKE_ROOT}/system.json.bak"
}

start_api() {
  local cmd_pid=""
  local app_ref=""

  pushd "${REPO_ROOT}" >/dev/null

  if command -v pypnm-cmts >/dev/null 2>&1; then
    if pypnm-cmts --help 2>/dev/null | grep -qE '(^|[[:space:]])api($|[[:space:]])'; then
      pypnm-cmts api --host "${HOST}" --port "${PORT}" --log-level "${LOG_LEVEL}" >/dev/null 2>&1 &
      cmd_pid="$!"
    fi
  fi

  if [[ -z "${cmd_pid}" ]]; then
    require_cmd python
    app_ref="$(detect_uvicorn_app)"
    if [[ -z "${app_ref}" ]]; then
      popd >/dev/null
      die "Unable to auto-detect FastAPI app reference for uvicorn (tried common module paths)."
    fi
    python -m uvicorn "${app_ref}" --host "${HOST}" --port "${PORT}" --log-level "${LOG_LEVEL}" >/dev/null 2>&1 &
    cmd_pid="$!"
  fi

  SERVER_PID="${cmd_pid}"

  local attempts=0
  until curl -sS "${BASE_URL}/ops/health" >/dev/null 2>&1; do
    attempts=$((attempts + 1))
    if [[ "${attempts}" -ge 60 ]]; then
      die "API did not become ready on ${BASE_URL} within timeout."
    fi
    sleep 0.2
  done

  popd >/dev/null
}

stop_api() {
  if [[ -n "${SERVER_PID}" ]]; then
    kill "${SERVER_PID}" >/dev/null 2>&1 || true
    wait "${SERVER_PID}" >/dev/null 2>&1 || true
    SERVER_PID=""
  fi
}

spawn_fake_process() {
  local argv="$1"
  local seconds="${2:-120}"

  bash -c "exec -a '${argv}' sleep '${seconds}'" >/dev/null 2>&1 &
  local pid="$!"
  FAKE_PIDS+=("${pid}")
  echo "${pid}"
}

make_pidfiles() {
  local state_dir="$1"
  local controller_pid="$2"
  local worker_pid="$3"

  mkdir -p "${state_dir}/pids"
  printf '%s\n' "${controller_pid}" > "${state_dir}/pids/controller.pid"
  printf '%s\n' "${worker_pid}" > "${state_dir}/pids/worker_7.pid"
}

remove_pidfiles() {
  local state_dir="$1"
  rm -rf "${state_dir}/pids" >/dev/null 2>&1 || true
}

echo "Smoke Test: Operational Endpoints"
echo "Repo: ${REPO_ROOT}"
echo "Base URL: ${BASE_URL}"
echo

require_cmd curl
require_cmd python

# -----------------------------------------------------------------------------
# Scenario A: Controller mode, state_dir should be created, /ready should be 200
# -----------------------------------------------------------------------------
ELECTION_A="ops-smoke-a"
STATE_A="${SMOKE_STATE_DIR_BASE}/a"

write_system_json "controller" "${STATE_A}" "${ELECTION_A}" "false" "false"
swap_in_config
start_api

body="$(curl_json "/ops/health" "200")"
assert_eq "/ops/health.status" "$(printf '%s' "${body}" | json_get "status")" "ok"
assert_non_empty "/ops/health.timestamp" "$(printf '%s' "${body}" | json_get "timestamp")"

body="$(curl_json "/ops/version" "200")"
assert_eq "/ops/version.application" "$(printf '%s' "${body}" | json_get "application")" "pypnm-cmts"
assert_non_empty "/ops/version.version" "$(printf '%s' "${body}" | json_get "version")"
assert_non_empty "/ops/version.python_version" "$(printf '%s' "${body}" | json_get "python_version")"
assert_non_empty "/ops/version.timestamp" "$(printf '%s' "${body}" | json_get "timestamp")"

body="$(curl_json "/ops/ready" "200")"
assert_eq "/ops/ready.status" "$(printf '%s' "${body}" | json_get "status")" "ok"
[[ -d "${STATE_A}" ]] || die "Controller scenario: expected state_dir to exist: ${STATE_A}"
[[ -d "${STATE_A}/pids" ]] || die "Controller scenario: expected pids dir: ${STATE_A}/pids"
[[ -d "${STATE_A}/logs" ]] || die "Controller scenario: expected logs dir: ${STATE_A}/logs"
[[ -d "${STATE_A}/inventory" ]] || die "Controller scenario: expected inventory dir: ${STATE_A}/inventory"

# /status with pidfiles missing
remove_pidfiles "${STATE_A}"
body="$(curl_json "/ops/status" "200")"
assert_eq "/ops/status.pid_records_missing" "$(printf '%s' "${body}" | json_get "pid_records_missing")" "True"
assert_eq "/ops/status.fallback_used" "$(printf '%s' "${body}" | json_get "fallback_used")" "False"

# /status with pidfiles present and running
fake_controller_pid="$(spawn_fake_process "pypnm-cmts run-forever --election-name=${ELECTION_A} --mode=controller" 180)"
fake_worker_pid="$(spawn_fake_process "pypnm-cmts run-forever --election-name=${ELECTION_A} --mode=worker --sg-id=7" 180)"
make_pidfiles "${STATE_A}" "${fake_controller_pid}" "${fake_worker_pid}"

body="$(curl_json "/ops/status" "200")"
assert_eq "/ops/status.pid_records_missing" "$(printf '%s' "${body}" | json_get "pid_records_missing")" "False"
assert_eq "/ops/status.pid_records_stale" "$(printf '%s' "${body}" | json_get "pid_records_stale")" "False"

# /status fallback behavior: remove pidfiles but keep matching processes running
remove_pidfiles "${STATE_A}"
body="$(curl_json "/ops/status" "200")"
assert_eq "/ops/status.fallback_used" "$(printf '%s' "${body}" | json_get "fallback_used")" "True"

stop_api
echo "Scenario A: PASS"
echo

# -----------------------------------------------------------------------------
# Scenario B: Worker mode, sg_id missing => /ready should be 503 + failed_check=worker_sg
# -----------------------------------------------------------------------------
ELECTION_B="ops-smoke-b"
STATE_B="${SMOKE_STATE_DIR_BASE}/b"
mkdir -p "${STATE_B}"

write_system_json "worker" "${STATE_B}" "${ELECTION_B}" "false" "false"
swap_in_config
start_api

body="$(curl_json "/ops/ready" "503")"
assert_eq "/ops/ready.status" "$(printf '%s' "${body}" | json_get "status")" "error"
assert_eq "/ops/ready.failed_check" "$(printf '%s' "${body}" | json_get "failed_check")" "worker_sg"

stop_api
echo "Scenario B: PASS"
echo

# -----------------------------------------------------------------------------
# Scenario C: Worker mode, sg_id present but state_dir missing => /ready should be 503 + failed_check=state_dir
# -----------------------------------------------------------------------------
ELECTION_C="ops-smoke-c"
STATE_C="${SMOKE_STATE_DIR_BASE}/c"
rm -rf "${STATE_C}" >/dev/null 2>&1 || true

write_system_json "worker" "${STATE_C}" "${ELECTION_C}" "true" "true"
swap_in_config
start_api

body="$(curl_json "/ops/ready" "503")"
assert_eq "/ops/ready.status" "$(printf '%s' "${body}" | json_get "status")" "error"
assert_eq "/ops/ready.failed_check" "$(printf '%s' "${body}" | json_get "failed_check")" "state_dir"

stop_api
echo "Scenario C: PASS"
echo

echo "Smoke test complete: ALL PASS"
