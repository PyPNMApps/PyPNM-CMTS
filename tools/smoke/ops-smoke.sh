# FILE: tools/smoke/ops-smoke.sh
#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

set -euo pipefail
IFS=$'\n\t'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=tools/smoke/lib/smoke-lib.sh
source "${SCRIPT_DIR}/lib/smoke-lib.sh"

smoke_require_cmd curl
smoke_require_cmd python
smoke_require_cmd uvicorn
smoke_require_cmd ps

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8801}"
BASE_URL="${BASE_URL:-http://${HOST}:${PORT}}"
LOG_LEVEL="${LOG_LEVEL:-info}"
SMOKE_KEEP_TMP="${SMOKE_KEEP_TMP:-0}"

SMOKE_TMP_DIR="$(smoke_mktemp_dir)"
API_LOG_PATH="${SMOKE_TMP_DIR}/api.log"
BODY_PATH="${SMOKE_TMP_DIR}/body"
ERR_PATH="${SMOKE_TMP_DIR}/err"
PID_BACKUP_DIR="${SMOKE_TMP_DIR}/pids.backup"

UVICORN_APP="${UVICORN_APP:-}"
API_PID=""

cleanup() {
  if [[ -n "${API_PID}" ]]; then
    kill "${API_PID}" >/dev/null 2>&1 || true
    wait "${API_PID}" >/dev/null 2>&1 || true
  fi

  if [[ "${SMOKE_KEEP_TMP}" == "1" ]]; then
    smoke_warn "Keeping smoke temp dir: ${SMOKE_TMP_DIR}"
    smoke_warn "Uvicorn log: ${API_LOG_PATH}"
    return 0
  fi

  rm -rf "${SMOKE_TMP_DIR}" || true
}
trap cleanup EXIT

tail_api_log() {
  if [[ -s "${API_LOG_PATH}" ]]; then
    smoke_err "Last 200 lines of uvicorn log:"
    tail -n 200 "${API_LOG_PATH}" >&2 || true
    return 0
  fi
  smoke_err "Uvicorn log is empty: ${API_LOG_PATH}"
  return 0
}

detect_uvicorn_app() {
  local candidates=(
    "pypnm_cmts.api.app:app"
    "pypnm_cmts.api.main:app"
    "pypnm_cmts.api.server:app"
    "pypnm_cmts.api:app"
    "pypnm_cmts.main:app"
  )

  python - "${candidates[@]}" <<'PY'
import importlib
import sys

candidates = sys.argv[1:]
for ref in candidates:
    try:
        mod_name, attr = ref.split(":", 1)
        mod = importlib.import_module(mod_name)
        getattr(mod, attr)
        print(ref)
        raise SystemExit(0)
    except Exception:
        continue
raise SystemExit(1)
PY
}

start_api() {
  if [[ -z "${UVICORN_APP}" ]]; then
    if ! UVICORN_APP="$(detect_uvicorn_app)"; then
      smoke_die "Unable to auto-detect uvicorn app reference. Set UVICORN_APP='<module>:<app>'."
    fi
  fi

  : >"${API_LOG_PATH}"
  uvicorn "${UVICORN_APP}" \
    --host "${HOST}" \
    --port "${PORT}" \
    --log-level "${LOG_LEVEL}" \
    >"${API_LOG_PATH}" 2>&1 &

  API_PID="$!"

  smoke_info "Smoke Test Suite: /ops"
  smoke_info "Base URL: ${BASE_URL}"
  smoke_info "Uvicorn App: ${UVICORN_APP}"

  if ! smoke_wait_for_url_ok "${BASE_URL}/ops/health" "${SMOKE_STARTUP_TIMEOUT_SECONDS}"; then
    tail_api_log
    exit 1
  fi
}

http_get_expect() {
  local path="$1"
  local expected_code="$2"

  local url="${BASE_URL}${path}"
  local code
  code="$(smoke_http_get "${url}" "${BODY_PATH}" "${ERR_PATH}")"

  if [[ "${code}" != "${expected_code}" ]]; then
    SMOKE_KEEP_TMP=1
    smoke_err "HTTP ${url}: expected ${expected_code}, got ${code}"
    if [[ -s "${ERR_PATH}" ]]; then
      smoke_err "curl stderr:"
      sed -e 's/^/  /' "${ERR_PATH}" >&2 || true
    fi
    if [[ -s "${BODY_PATH}" ]]; then
      smoke_err "response body:"
      sed -e 's/^/  /' "${BODY_PATH}" >&2 || true
    else
      smoke_err "response body: <empty>"
    fi
    tail_api_log
    exit 1
  fi
}

test_health() {
  http_get_expect "/ops/health" "200"
  smoke_assert_json_equals "${BODY_PATH}" "status" "ok" "/ops/health.status"
  local state_dir
  state_dir="$(smoke_json_get "${BODY_PATH}" "meta.state_dir" || true)"
  [[ -n "${state_dir}" ]] || smoke_die "/ops/health.meta.state_dir is empty; cannot continue."
  smoke_info "state_dir: ${state_dir}"
}

test_ready() {
  local url="${BASE_URL}/ops/ready"
  local code
  code="$(smoke_http_get "${url}" "${BODY_PATH}" "${ERR_PATH}")"

  if [[ "${code}" == "200" ]]; then
    smoke_assert_json_equals "${BODY_PATH}" "status" "ok" "/ops/ready.status(200)"
    return 0
  fi

  if [[ "${code}" == "503" ]]; then
    smoke_assert_json_equals "${BODY_PATH}" "status" "error" "/ops/ready.status(503)"
    local failed
    failed="$(smoke_json_get "${BODY_PATH}" "failed_check" || true)"
    [[ -n "${failed}" ]] || smoke_die "/ops/ready.failed_check is empty on 503."
    smoke_info "/ops/ready returned 503 as expected for current runtime config (failed_check=${failed})."
    return 0
  fi

  SMOKE_KEEP_TMP=1
  smoke_err "HTTP ${url}: unexpected status ${code}"
  tail_api_log
  exit 1
}

test_version() {
  http_get_expect "/ops/version" "200"
  smoke_assert_json_equals "${BODY_PATH}" "application" "pypnm-cmts" "/ops/version.application"
  local version
  version="$(smoke_json_get "${BODY_PATH}" "version" || true)"
  [[ -n "${version}" ]] || smoke_die "/ops/version.version is empty."
}

test_status_baseline() {
  http_get_expect "/ops/status" "200"
  local status
  status="$(smoke_json_get "${BODY_PATH}" "status" || true)"
  [[ -n "${status}" ]] || smoke_die "/ops/status.status is empty."
}

main() {
  start_api

  test_health
  test_ready
  test_version

  test_status_baseline

  smoke_info "OK: /ops smoke tests passed."
}

main "$@"
