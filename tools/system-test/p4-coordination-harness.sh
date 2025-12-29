#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

set -euo pipefail
IFS=$'\n\t'

SCRIPT_NAME="$(basename "$0")"

usage() {
  cat <<EOF
Usage:
  ${SCRIPT_NAME} start  --cmts-hostname <ip> --read-community <str> --write-community <str> --cmts-port <port> --state-dir <dir> --election-name <name>
  ${SCRIPT_NAME} stop   --state-dir <dir>
  ${SCRIPT_NAME} status --state-dir <dir>
  ${SCRIPT_NAME} verify --state-dir <dir>

Notes:
  - start launches controller + 1 worker per discovered service group (SG).
  - logs:   <state-dir>/logs/controller.log, worker_<sg>.log
  - pids:   <state-dir>/pids/controller.pid, worker_<sg>.pid
  - env:    <state-dir>/run.env (used by status/verify)
EOF
}

die() {
  echo "ERROR: $*" 1>&2
  exit 1
}

require_arg() {
  local name="$1"
  local value="$2"
  if [[ -z "${value}" ]]; then
    die "Missing required argument: ${name}"
  fi
}

ensure_dirs() {
  local state_dir="$1"
  mkdir -p "${state_dir}/logs"
  mkdir -p "${state_dir}/pids"
  mkdir -p "${state_dir}/inventory"
}

write_run_env() {
  local state_dir="$1"
  local election_name="$2"
  local cmts_host="$3"
  local cmts_port="$4"

  cat > "${state_dir}/run.env" <<EOF
STATE_DIR=${state_dir}
ELECTION_NAME=${election_name}
CMTS_HOST=${cmts_host}
CMTS_PORT=${cmts_port}
EOF
}

load_run_env() {
  local state_dir="$1"
  local run_env="${state_dir}/run.env"

  if [[ -f "${run_env}" ]]; then
    # shellcheck disable=SC1090
    source "${run_env}"
  else
    STATE_DIR="${state_dir}"
    ELECTION_NAME="${ELECTION_NAME:-}"
    CMTS_HOST="${CMTS_HOST:-}"
    CMTS_PORT="${CMTS_PORT:-161}"
  fi
}

pid_is_running() {
  local pid_file="$1"

  if [[ ! -f "${pid_file}" ]]; then
    return 1
  fi

  local pid
  pid="$(cat "${pid_file}" 2>/dev/null || true)"
  if [[ -z "${pid}" ]]; then
    return 1
  fi

  if kill -0 "${pid}" 2>/dev/null; then
    return 0
  fi

  return 1
}

kill_pid_file() {
  local pid_file="$1"

  if [[ ! -f "${pid_file}" ]]; then
    return 0
  fi

  local pid
  pid="$(cat "${pid_file}" 2>/dev/null || true)"
  if [[ -z "${pid}" ]]; then
    rm -f "${pid_file}"
    return 0
  fi

  if kill -0 "${pid}" 2>/dev/null; then
    kill "${pid}" 2>/dev/null || true

    for _ in 1 2 3 4 5 6 7 8 9 10; do
      if ! kill -0 "${pid}" 2>/dev/null; then
        break
      fi
      sleep 0.2
    done

    if kill -0 "${pid}" 2>/dev/null; then
      kill -9 "${pid}" 2>/dev/null || true
    fi
  fi

  rm -f "${pid_file}"
}

discover_sg_ids() {
  local discovery_json="$1"
  local -a sg_ids=()

  if [[ ! -f "${discovery_json}" ]]; then
    echo ""
    return 0
  fi

  local out
  out="$(python3 - <<'PY' "${discovery_json}"
import json
import sys
import re

path = sys.argv[1]
with open(path, "r", encoding="utf-8") as f:
    data = json.load(f)

raw = data.get("discovered_sg_ids", [])
tokens: list[str] = []

if isinstance(raw, list):
    for v in raw:
        s = str(v).strip()
        if not s:
            continue
        tokens.extend(re.split(r"[,\s]+", s))
else:
    s = str(raw).strip()
    if s:
        tokens.extend(re.split(r"[,\s]+", s))

sg_ids: list[int] = []
seen: set[int] = set()
for t in tokens:
    if not t:
        continue
    try:
        v = int(t)
    except Exception:
        continue
    if v in seen:
        continue
    seen.add(v)
    sg_ids.append(v)

for v in sg_ids:
    print(v)
PY
)"

  if [[ -n "${out}" ]]; then
    while IFS= read -r line; do
      [[ -n "${line}" ]] && sg_ids+=("${line}")
    done <<< "${out}"
  fi

  if [[ "${#sg_ids[@]}" -eq 0 ]]; then
    echo ""
    return 0
  fi

  printf "%s\n" "${sg_ids[@]}"
}

build_exec_prefix() {
  local -n out="$1"
  out=(env PYTHONUNBUFFERED=1)
  if command -v stdbuf >/dev/null 2>&1; then
    out+=(stdbuf -oL -eL)
  fi
}

run_controller() {
  local state_dir="$1"
  local election_name="$2"
  local cmts_host="$3"
  local cmts_port="$4"
  local read_comm="$5"
  local write_comm="$6"

  local log_file="${state_dir}/logs/controller.log"
  local pid_file="${state_dir}/pids/controller.pid"

  local -a prefix
  build_exec_prefix prefix

  nohup "${prefix[@]}" pypnm-cmts run-forever \
    --mode controller \
    --cmts-hostname "${cmts_host}" \
    --read-community "${read_comm}" \
    --write-community "${write_comm}" \
    --cmts-port "${cmts_port}" \
    --state-dir "${state_dir}" \
    --election-name "${election_name}" \
    --tick-interval-seconds 1 \
    > "${log_file}" 2>&1 &

  echo "$!" > "${pid_file}"
  echo "Controller started (pid=$(cat "${pid_file}"))"
}

run_worker() {
  local state_dir="$1"
  local election_name="$2"
  local cmts_host="$3"
  local cmts_port="$4"
  local read_comm="$5"
  local write_comm="$6"
  local sg_id="$7"

  local pid_file="${state_dir}/pids/worker_${sg_id}.pid"
  local log_file="${state_dir}/logs/worker_${sg_id}.log"
  local owner_id="worker-${sg_id}"

  local -a prefix
  build_exec_prefix prefix

  nohup "${prefix[@]}" pypnm-cmts run-forever \
    --mode worker \
    --cmts-hostname "${cmts_host}" \
    --read-community "${read_comm}" \
    --write-community "${write_comm}" \
    --cmts-port "${cmts_port}" \
    --state-dir "${state_dir}" \
    --election-name "${election_name}" \
    --sg-id "${sg_id}" \
    --owner-id "${owner_id}" \
    --tick-interval-seconds 1 \
    > "${log_file}" 2>&1 &

  echo "$!" > "${pid_file}"
  echo "Worker ${sg_id} started (pid=$(cat "${pid_file}"))"
}

show_status() {
  local state_dir="$1"

  load_run_env "${state_dir}"

  echo "STATE_DIR=${STATE_DIR}"
  echo "ELECTION_NAME=${ELECTION_NAME}"
  echo "CMTS_HOST=${CMTS_HOST}"
  echo "CMTS_PORT=${CMTS_PORT}"
  echo

  local controller_pid="${state_dir}/pids/controller.pid"
  if pid_is_running "${controller_pid}"; then
    echo "Controller: RUNNING (pid=$(cat "${controller_pid}"))"
  else
    echo "Controller: STOPPED"
  fi

  if [[ -d "${state_dir}/pids" ]]; then
    local pid_file
    for pid_file in "${state_dir}/pids"/worker_*.pid; do
      [[ -e "${pid_file}" ]] || continue
      local base
      base="$(basename "${pid_file}")"
      if [[ ! "${base}" =~ ^worker_[0-9]+\.pid$ ]]; then
        continue
      fi
      if pid_is_running "${pid_file}"; then
        echo "${base}: RUNNING (pid=$(cat "${pid_file}"))"
      else
        echo "${base}: STOPPED"
      fi
    done
  fi

  local discovery="${state_dir}/inventory/discovery.json"
  if [[ -f "${discovery}" ]]; then
    echo
    echo "Discovery: PRESENT (${discovery})"
  fi
}

tail_controller_log() {
  local state_dir="$1"
  local log_file="${state_dir}/logs/controller.log"
  if [[ -f "${log_file}" ]]; then
    echo
    echo "---- tail -n 200 ${log_file} ----"
    tail -n 200 "${log_file}" || true
  fi
}

wait_for_controller_json() {
  local controller_log="$1"
  local tries=0
  while [[ "${tries}" -lt 120 ]]; do
    if grep -q '"mode"[[:space:]]*:[[:space:]]*"controller"' "${controller_log}" 2>/dev/null; then
      return 0
    fi
    sleep 0.25
    tries="$((tries + 1))"
  done
  return 1
}

wait_for_worker_json() {
  local worker_log="$1"
  local tries=0
  while [[ "${tries}" -lt 120 ]]; do
    if grep -q '"mode"[[:space:]]*:[[:space:]]*"worker"' "${worker_log}" 2>/dev/null; then
      return 0
    fi
    sleep 0.25
    tries="$((tries + 1))"
  done
  return 1
}

verify_phase4() {
  local state_dir="$1"
  local leader_retry_max=15
  local leader_retry_sleep=1

  load_run_env "${state_dir}"

  echo "STATE_DIR=${STATE_DIR}"
  echo "ELECTION_NAME=${ELECTION_NAME}"
  echo "CMTS_HOST=${CMTS_HOST}"
  echo "CMTS_PORT=${CMTS_PORT}"
  echo

  local controller_pid="${state_dir}/pids/controller.pid"
  if ! pid_is_running "${controller_pid}"; then
    die "VERIFY_FAIL: Controller not running: ${controller_pid}"
  fi
  echo "Controller: RUNNING (pid=$(cat "${controller_pid}"))"

  local discovery="${state_dir}/inventory/discovery.json"
  if [[ ! -f "${discovery}" ]]; then
    die "VERIFY_FAIL: Discovery missing: ${discovery}"
  fi
  echo "Discovery: PRESENT (${discovery})"

  local controller_log="${state_dir}/logs/controller.log"
  if [[ ! -s "${controller_log}" ]]; then
    tail_log_or_empty "${controller_log}" 120
    die "VERIFY_FAIL: No controller log output found in ${controller_log}"
  fi

  if ! wait_for_controller_json "${controller_log}"; then
    tail_log_or_empty "${controller_log}" 120
    die "VERIFY_FAIL: No controller JSON lines found after waiting"
  fi

  check_controller_leader() {
    python3 - <<'PY' "${controller_log}"
import json
import sys

path = sys.argv[1]
last = None
with open(path, "r", encoding="utf-8", errors="replace") as f:
    for line in f:
        line = line.strip()
        if not line or not line.startswith("{"):
            continue
        try:
            obj = json.loads(line)
        except Exception:
            continue
        if obj.get("mode") == "controller":
            last = obj

if last is None:
    raise SystemExit("VERIFY_FAIL: No controller JSON lines found")

if not (last.get("coordination_tick") or {}).get("is_leader", False):
    raise SystemExit("VERIFY_FAIL: Controller is_leader != true")

leased = (last.get("coordination_tick") or {}).get("leased_sg_ids", None)
if leased is None or leased != []:
    raise SystemExit(f"VERIFY_FAIL: Controller leased_sg_ids expected [], got {leased}")

print("Controller: OK (is_leader=true, leased_sg_ids=[])")
PY
  }

  local leader_attempt=0
  until check_controller_leader; do
    leader_attempt="$((leader_attempt + 1))"
    if [[ "${leader_attempt}" -ge "${leader_retry_max}" ]]; then
      tail_log_or_empty "${controller_log}" 160
      die "VERIFY_FAIL: Controller is_leader != true"
    fi
    sleep "${leader_retry_sleep}"
  done

  local -a worker_pid_files=()
  if [[ -d "${state_dir}/pids" ]]; then
    local p
    for p in "${state_dir}/pids"/worker_*.pid; do
      [[ -e "${p}" ]] || continue
      local base
      base="$(basename "${p}")"
      if [[ ! "${base}" =~ ^worker_[0-9]+\.pid$ ]]; then
        continue
      fi
      worker_pid_files+=("${p}")
    done
  fi

  if [[ "${#worker_pid_files[@]}" -eq 0 ]]; then
    die "VERIFY_FAIL: No worker pid files present under ${state_dir}/pids"
  fi

  local any_worker_ok="false"
  local pid_file
  for pid_file in "${worker_pid_files[@]}"; do
    local base
    base="$(basename "${pid_file}")"
    if [[ ! "${base}" =~ ^worker_[0-9]+\.pid$ ]]; then
      continue
    fi

    if ! pid_is_running "${pid_file}"; then
      echo "Worker: NOT RUNNING (${base})"
      continue
    fi

    local sg_id
    sg_id="${base#worker_}"
    sg_id="${sg_id%.pid}"

    local worker_log="${state_dir}/logs/worker_${sg_id}.log"
    if [[ ! -s "${worker_log}" ]]; then
      echo "Worker: NO LOG OUTPUT (sg_id=${sg_id})"
      continue
    fi
    if ! wait_for_worker_json "${worker_log}"; then
      echo "Worker: NO WORKER JSON (sg_id=${sg_id})"
      continue
    fi

    python3 - <<'PY' "${worker_log}" "${sg_id}"
import json
import sys

path = sys.argv[1]
sg_id = int(sys.argv[2])

seen_worker_json = 0
seen_lease_held = False
seen_sg_activity = False
seen_work_results = False

def tick_sg_ids(obj: dict) -> set[int]:
    tick = obj.get("coordination_tick") or {}
    sg_ids: set[int] = set()
    for key in ("acquired_sg_ids", "renewed_sg_ids", "leased_sg_ids"):
        vals = tick.get(key) or []
        for v in vals:
            try:
                sg_ids.add(int(v))
            except Exception:
                pass
    return sg_ids

with open(path, "r", encoding="utf-8", errors="replace") as f:
    for line in f:
        line = line.strip()
        if not line or not line.startswith("{"):
            continue
        try:
            obj = json.loads(line)
        except Exception:
            continue
        if obj.get("mode") != "worker":
            continue

        seen_worker_json += 1

        if obj.get("lease_held", False):
            seen_lease_held = True

        if sg_id in tick_sg_ids(obj):
            seen_sg_activity = True

        wr = obj.get("work_results") or []
        if isinstance(wr, list) and len(wr) > 0:
            seen_work_results = True

if seen_worker_json == 0:
    raise SystemExit("NO_WORKER_JSON")
if not seen_lease_held:
    raise SystemExit("LEASE_NOT_HELD")
if not seen_sg_activity:
    raise SystemExit("NO_SG_ACQUIRE_OR_RENEW")
if not seen_work_results:
    raise SystemExit("WORK_RESULTS_EMPTY")

print("WORKER_OK")
PY
    rc="$?"
    if [[ "${rc}" -eq 0 ]]; then
      echo "Worker: OK (sg_id=${sg_id}, lease_held=true, acquired/renew present, work_results non-empty)"
      any_worker_ok="true"
    else
      echo "Worker: FAIL (sg_id=${sg_id})"
    fi
  done

  if [[ "${any_worker_ok}" != "true" ]]; then
    die "VERIFY_FAIL: No workers satisfied Phase 4 criteria"
  fi

  echo
  echo "VERIFY_OK: Phase 4 criteria satisfied."
}

cmd_start() {
  local cmts_host=""
  local cmts_port="161"
  local read_comm=""
  local write_comm=""
  local state_dir=""
  local election_name=""

  while [[ "${#}" -gt 0 ]]; do
    case "$1" in
      --cmts-hostname) cmts_host="${2:-}"; shift 2 ;;
      --cmts-port) cmts_port="${2:-}"; shift 2 ;;
      --read-community) read_comm="${2:-}"; shift 2 ;;
      --write-community) write_comm="${2:-}"; shift 2 ;;
      --state-dir) state_dir="${2:-}"; shift 2 ;;
      --election-name) election_name="${2:-}"; shift 2 ;;
      -h|--help) usage; exit 0 ;;
      *) die "Unknown argument: $1" ;;
    esac
  done

  require_arg "--cmts-hostname" "${cmts_host}"
  require_arg "--read-community" "${read_comm}"
  require_arg "--write-community" "${write_comm}"
  require_arg "--state-dir" "${state_dir}"
  require_arg "--election-name" "${election_name}"

  ensure_dirs "${state_dir}"
  write_run_env "${state_dir}" "${election_name}" "${cmts_host}" "${cmts_port}"

  echo "STATE_DIR=${state_dir}"
  echo "ELECTION_NAME=${election_name}"
  echo "CMTS_HOST=${cmts_host}"
  echo "CMTS_PORT=${cmts_port}"
  echo

  run_controller "${state_dir}" "${election_name}" "${cmts_host}" "${cmts_port}" "${read_comm}" "${write_comm}"

  local controller_pid_file="${state_dir}/pids/controller.pid"
  local discovery="${state_dir}/inventory/discovery.json"
  local tries=0

  while [[ "${tries}" -lt 60 ]]; do
    if [[ -f "${discovery}" ]]; then
      break
    fi

    if ! pid_is_running "${controller_pid_file}"; then
      tail_controller_log "${state_dir}"
      die "Controller exited before discovery file was created: ${discovery}"
    fi

    sleep 0.5
    tries="$((tries + 1))"
  done

  if [[ ! -f "${discovery}" ]]; then
    tail_controller_log "${state_dir}"
    die "Discovery file not created: ${discovery}"
  fi

  local -a sg_ids=()
  local sg_id
  while IFS= read -r sg_id; do
    [[ -n "${sg_id}" ]] && sg_ids+=("${sg_id}")
  done < <(discover_sg_ids "${discovery}")

  if [[ "${#sg_ids[@]}" -eq 0 ]]; then
    die "No service groups discovered in ${discovery}"
  fi

  for sg_id in "${sg_ids[@]}"; do
    run_worker "${state_dir}" "${election_name}" "${cmts_host}" "${cmts_port}" "${read_comm}" "${write_comm}" "${sg_id}"
  done
}

cmd_stop() {
  local state_dir=""

  while [[ "${#}" -gt 0 ]]; do
    case "$1" in
      --state-dir) state_dir="${2:-}"; shift 2 ;;
      -h|--help) usage; exit 0 ;;
      *) die "Unknown argument: $1" ;;
    esac
  done

  require_arg "--state-dir" "${state_dir}"

  local pids_dir="${state_dir}/pids"
  if [[ ! -d "${pids_dir}" ]]; then
    echo "Stopped."
    return 0
  fi

  local pid_file
  for pid_file in "${pids_dir}"/worker_*.pid; do
    [[ -e "${pid_file}" ]] || continue
    local base
    base="$(basename "${pid_file}")"
    if [[ ! "${base}" =~ ^worker_[0-9]+\.pid$ ]]; then
      continue
    fi
    echo "Stopping ${base} (pid=$(cat "${pid_file}" 2>/dev/null || true))"
    kill_pid_file "${pid_file}"
  done

  local controller_pid="${pids_dir}/controller.pid"
  if [[ -f "${controller_pid}" ]]; then
    echo "Stopping controller (pid=$(cat "${controller_pid}" 2>/dev/null || true))"
    kill_pid_file "${controller_pid}"
  fi

  echo "Stopped."
}

cmd_status() {
  local state_dir=""

  while [[ "${#}" -gt 0 ]]; do
    case "$1" in
      --state-dir) state_dir="${2:-}"; shift 2 ;;
      -h|--help) usage; exit 0 ;;
      *) die "Unknown argument: $1" ;;
    esac
  done

  require_arg "--state-dir" "${state_dir}"
  show_status "${state_dir}"
}

cmd_verify() {
  local state_dir=""

  while [[ "${#}" -gt 0 ]]; do
    case "$1" in
      --state-dir) state_dir="${2:-}"; shift 2 ;;
      -h|--help) usage; exit 0 ;;
      *) die "Unknown argument: $1" ;;
    esac
  done

  require_arg "--state-dir" "${state_dir}"
  verify_phase4 "${state_dir}"
}

main() {
  if [[ "${#}" -lt 1 ]]; then
    usage
    exit 2
  fi

  local cmd="$1"
  shift

  case "${cmd}" in
    start) cmd_start "$@" ;;
    stop) cmd_stop "$@" ;;
    status) cmd_status "$@" ;;
    verify) cmd_verify "$@" ;;
    -h|--help) usage; exit 0 ;;
    *) die "Unknown command: ${cmd}" ;;
  esac
}

main "$@"
