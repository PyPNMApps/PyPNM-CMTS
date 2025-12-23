#!/usr/bin/env bash
set -euo pipefail

# Silent alias installer for PyPNM-CMTS.
# - No echo / user-facing output.
# - Appends aliases to detected shell rc file.
# - Safe to re-run; skips aliases already present.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

detect_shell_rc_file() {
  if [[ -n "${ZSH_VERSION:-}" && -f "${HOME}/.zshrc" ]]; then
    echo "${HOME}/.zshrc"
    return
  fi

  if [[ -n "${BASH_VERSION:-}" && -f "${HOME}/.bashrc" ]]; then
    echo "${HOME}/.bashrc"
    return
  fi

  if [[ -f "${HOME}/.bashrc" ]]; then
    echo "${HOME}/.bashrc"
    return
  fi

  if [[ -f "${HOME}/.zshrc" ]]; then
    echo "${HOME}/.zshrc"
    return
  fi

  echo "${HOME}/.profile"
}

RC_FILE="${PYPNM_CMTS_SHELL_RC:-$(detect_shell_rc_file)}"

mkdir -p "$(dirname "${RC_FILE}")"
if [[ ! -f "${RC_FILE}" ]]; then
  : > "${RC_FILE}"
fi

if ! grep -Fq "# PyPNM-CMTS aliases" "${RC_FILE}" 2>/dev/null; then
  {
    printf '\n'
    printf '# PyPNM-CMTS aliases\n'
  } >> "${RC_FILE}"
fi

append_alias() {
  local line="$1"
  if grep -Fq "${line}" "${RC_FILE}" 2>/dev/null; then
    return
  fi
  printf '%s\n' "${line}" >> "${RC_FILE}"
}

# ---------------------------------------------------------------------------
# Alias definitions
# ---------------------------------------------------------------------------

append_alias "alias pypnm-cmts-clean='cd \"${PROJECT_ROOT}\" && ./tools/maintenance/clean.sh'"
append_alias "alias pypnm-cmts-docs='cd \"${PROJECT_ROOT}\" && mkdocs serve'"
append_alias "alias pypnm-cmts-api='cd \"${PROJECT_ROOT}\" && python -m pypnm_cmts.api.main'"
append_alias "alias pycmts-clean='cd \"${PROJECT_ROOT}\" && ./tools/maintenance/clean.sh'"

# Example placeholder for future aliases (keep but commented-out for now):
# append_alias "alias pypnm-cmts-env='cd \"${PROJECT_ROOT}\" && source .env/bin/activate'"
