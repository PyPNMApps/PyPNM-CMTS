#!/usr/bin/env bash
set -euo pipefail

VENV_DIR="${1:-.env}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

if [[ ! -d "${VENV_DIR}" ]]; then
  echo "Virtual environment not found at ${VENV_DIR}"
  echo "Run ./install.sh [venv_dir] to create one."
  exit 1
fi

# shellcheck source=/dev/null
source "${VENV_DIR}/bin/activate"

python -m pip install --upgrade pip setuptools wheel
python -m pip install -e "${PROJECT_ROOT}[dev]"

python - <<'PYCODE'
import pypnm_cmts
print(f"Imported PyPNM-CMTS v{pypnm_cmts.__version__}")
PYCODE
