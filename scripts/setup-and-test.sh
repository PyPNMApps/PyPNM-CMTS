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

log_target="$(python - <<'PYCODE'
from __future__ import annotations

from pathlib import Path

try:
    import sys
    import pypnm
    from pypnm.config.system_config_settings import SystemConfigSettings
except Exception:
    print("")
    raise SystemExit(0)

def _site_packages_root(prefix: str) -> Path | None:
    lib_dir = Path(prefix) / "lib"
    if not lib_dir.exists():
        return None
    for python_dir in lib_dir.glob("python*"):
        candidate = python_dir / "site-packages" / "pypnm"
        if candidate.exists():
            return candidate.resolve()
    return None

package_root = _site_packages_root(sys.prefix)
if package_root is None:
    package_root = Path(pypnm.__file__).resolve().parent

config_path = package_root / "settings" / "system.json"
log_dir = Path(SystemConfigSettings.log_dir())

if not log_dir.is_absolute():
    log_dir = (config_path.parent.parent / log_dir).resolve()

print(log_dir)
PYCODE
)"

if [[ -n "${log_target}" ]]; then
  mkdir -p "${log_target}"
  if [[ -e "${PROJECT_ROOT}/logs" && ! -L "${PROJECT_ROOT}/logs" ]]; then
    echo "Logs path exists and is not a symlink; leaving as-is."
  else
    ln -sfn "${log_target}" "${PROJECT_ROOT}/logs"
  fi
fi

python - <<'PYCODE'
import pypnm_cmts
print(f"Imported PyPNM-CMTS v{pypnm_cmts.__version__}")
PYCODE
