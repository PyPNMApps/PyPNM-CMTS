#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR=".env"
UPDATE_PYPNM_DOCSIS="false"

usage() {
  cat <<'EOF'
Usage: ./install.sh [venv_dir] [--update-pypnm-docsis]

Options:
  --update-pypnm-docsis  Upgrade pypnm-docsis inside the venv before installing.
  -h, --help             Show this help.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --update-pypnm-docsis)
      UPDATE_PYPNM_DOCSIS="true"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    --*)
      echo "ERROR: Unknown option: $1" >&2
      usage
      exit 2
      ;;
    *)
      if [[ "${VENV_DIR}" != ".env" ]]; then
        echo "ERROR: Multiple venv directories provided." >&2
        usage
        exit 1
      fi
      if [[ "$1" == -* ]]; then
        echo "ERROR: Invalid venv directory: $1" >&2
        usage
        exit 1
      fi
      VENV_DIR="$1"
      shift
      ;;
  esac
done

if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 not found in PATH." >&2
  exit 1
fi

SETUP_SCRIPT="${SCRIPT_DIR}/scripts/setup-and-test.sh"
if [[ ! -f "${SETUP_SCRIPT}" ]]; then
  echo "ERROR: Missing script: ${SETUP_SCRIPT}" >&2
  exit 1
fi
if [[ ! -x "${SETUP_SCRIPT}" ]]; then
  echo "ERROR: Script is not executable: ${SETUP_SCRIPT}" >&2
  exit 1
fi

if [[ ! -d "${VENV_DIR}" ]]; then
  python3 -m venv "${VENV_DIR}"
fi

"${SETUP_SCRIPT}" "${VENV_DIR}" "${UPDATE_PYPNM_DOCSIS}"
