#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Local container preflight for PyPNM.

Usage:
  tools/local/local_container_build.sh [--smoke]

Options:
  --smoke   Build, start docker-compose, wait for health, then tear down.

Notes:
- Requires Docker and the docker compose plugin.
- Use sudo or add your user to the docker group if daemon access is denied.
EOF
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BANNER_PATH="${SCRIPT_DIR}/../banner.txt"

if [[ -f "${BANNER_PATH}" ]]; then
  cat "${BANNER_PATH}"
  echo
fi

run_smoke=false
if [[ ${1:-} == "--smoke" ]]; then
  run_smoke=true
elif [[ $# -gt 0 ]]; then
  usage
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "docker not found in PATH" >&2
  echo "See https://github.com/PyPNMApps/PyPNM/blob/main/docs/tools/local-container-build.md" \
       "or https://github.com/PyPNMApps/PyPNM/blob/main/docs/docker/install-docker.md for setup." >&2
  echo "Suggested (Debian/Ubuntu): sudo apt-get update && sudo apt-get install -y docker.io docker-buildx-plugin docker-compose-plugin" >&2
  exit 1
fi

compose_cmd=()
compose_supports_progress=false
if docker compose version >/dev/null 2>&1; then
  compose_cmd=(docker compose)
  compose_supports_progress=true
elif command -v docker-compose >/dev/null 2>&1; then
  compose_cmd=(docker-compose)
else
  echo "docker compose (plugin) not available; install or upgrade Docker" >&2
  echo "See https://github.com/PyPNMApps/PyPNM/blob/main/docs/tools/local-container-build.md for requirements." >&2
  echo "Suggested (Debian/Ubuntu): sudo apt-get install -y docker-compose" >&2
  echo "Or use the Docker CE repo and install docker-compose-plugin + docker-buildx-plugin." >&2
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 not found in PATH" >&2
  exit 1
fi

# Validate access to the daemon early (avoids permission-denied surprises mid-run)
if ! docker info >/dev/null 2>&1; then
  echo "Cannot talk to Docker daemon (permission denied?). Try running with sudo or add your user to the docker group." >&2
  exit 1
fi

SCRIPT_DIR="$(cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../.." && pwd)"
cd "$REPO_ROOT"

COMPOSE_FILE="${REPO_ROOT}/docker-compose.yml"
PYPNM_PORT="$(python3 - <<'PY'
import socket

s = socket.socket()
s.bind(("", 0))
print(s.getsockname()[1])
s.close()
PY
)"
export PYPNM_PORT

echo ">> Building compose images..."
if [[ "${compose_supports_progress}" == true ]]; then
  "${compose_cmd[@]}" -f "${COMPOSE_FILE}" --progress plain build
else
  "${compose_cmd[@]}" -f "${COMPOSE_FILE}" build
fi

if [[ "$run_smoke" != true ]]; then
  echo "✅ Build completed."
  exit 0
fi

cleanup() {
  echo ">> Tearing down stack..."
  "${compose_cmd[@]}" -f "${COMPOSE_FILE}" down --volumes >/dev/null 2>&1 || true
}
trap cleanup EXIT

export COMPOSE_PROJECT_NAME=pypnm-local-preflight
echo ">> Starting stack for health check..."
"${compose_cmd[@]}" -f "${COMPOSE_FILE}" up -d

echo ">> Waiting for pypnm-api to become healthy..."
cid="$("${compose_cmd[@]}" -f "${COMPOSE_FILE}" ps -q pypnm-api)"
if [[ -z "$cid" ]]; then
  echo "pypnm-api container not created" >&2
  exit 1
fi

for attempt in $(seq 1 20); do
  status="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$cid")"
  if [[ "$status" == "healthy" ]]; then
    echo "✅ pypnm-api is healthy."
    exit 0
  fi
  echo "Attempt ${attempt}/20: status=${status}; waiting..."
  sleep 3
done

echo "❌ pypnm-api did not become healthy."
"${compose_cmd[@]}" -f "${COMPOSE_FILE}" logs
exit 1
