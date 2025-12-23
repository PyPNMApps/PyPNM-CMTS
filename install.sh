#!/usr/bin/env bash
set -euo pipefail

VENV_DIR="${1:-.env}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ ! -d "${VENV_DIR}" ]]; then
  python3 -m venv "${VENV_DIR}"
fi

"${SCRIPT_DIR}/scripts/setup-and-test.sh" "${VENV_DIR}"
