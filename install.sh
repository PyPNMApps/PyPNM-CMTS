#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${SCRIPT_DIR}"
BANNER_PATH="${PROJECT_ROOT}/tools/banner.txt"
VENV_DIR=".env"
MODE="standard"
UPDATE_TAG=""
UPDATE_DEVELOPMENT_PYPNM_DOCSIS_TAG=""
CLEAN_MODE="0"
PURGE_CACHE="0"
UNINSTALL_MODE="0"
DEVELOPMENT_MODE="0"
UPDATE_GA_MODE="0"
UPDATE_HOT_FIX_MODE="0"
UPDATE_DEVELOPMENT_PYPNM_DOCSIS_MODE="0"
PM="none"
GITLEAKS_VERSION="8.18.1"
PREVIOUS_SYSTEM_CONFIG_PATH=""
SYSTEM_CONFIG_BACKUP_FILE=""
RESTORE_SYSTEM_CONFIG_AFTER_INSTALL="0"

usage() {
  cat <<'USAGE_EOF'
PyPNM-CMTS Installer

Usage:
  ./install.sh [venv_dir]
  ./install.sh --clean [--purge-cache] [venv_dir]
  ./install.sh --uninstall [venv_dir]
  ./install.sh --development [venv_dir]
  ./install.sh --update-ga [TAG] [venv_dir]
  ./install.sh --update-hot-fix [TAG] [venv_dir]
  ./install.sh --update-development-pypnm-docsis [TAG] [venv_dir]
  ./install.sh --help

Options:
  --development        Install dev prerequisites and run local verification.
  --update-ga [TAG]    Install the specified GA tag (latest GA if omitted).
  --update-hot-fix [TAG]
                       Install the specified hot-fix tag (latest hot-fix if omitted).
  --update-development-pypnm-docsis [TAG]
                       Upgrade pypnm-docsis in the active venv to the specified tag/version
                       (latest pre-release if omitted).
  --clean              Remove prior install artifacts before installing.
  --purge-cache        Purge pip cache after venv activation.
  --uninstall          Remove local install artifacts (cannot combine with other flags).
  --help, -h           Show this help message.

Examples:
  ./install.sh
  ./install.sh .env-dev
  ./install.sh --development
  ./install.sh --update-ga v0.1.39.0
  ./install.sh --update-hot-fix v0.1.39.1
  ./install.sh --update-development-pypnm-docsis
  ./install.sh --update-development-pypnm-docsis v1.4.2.0
USAGE_EOF
}

require_command() {
  local command_name="$1"
  if ! command -v "${command_name}" >/dev/null 2>&1; then
    echo "ERROR: ${command_name} not found in PATH." >&2
    exit 1
  fi
}

print_banner() {
  if [[ -f "${BANNER_PATH}" ]]; then
    cat "${BANNER_PATH}"
    echo
  fi
}

detect_package_manager() {
  if command -v apt-get >/dev/null 2>&1; then
    PM="apt"
    return
  fi
  if command -v dnf >/dev/null 2>&1; then
    PM="dnf"
    return
  fi
  if command -v yum >/dev/null 2>&1; then
    PM="yum"
    return
  fi
  if command -v zypper >/dev/null 2>&1; then
    PM="zypper"
    return
  fi
  if command -v apk >/dev/null 2>&1; then
    PM="apk"
    return
  fi
  if command -v brew >/dev/null 2>&1; then
    PM="brew"
    return
  fi
}

sudo_available() {
  if command -v sudo >/dev/null 2>&1; then
    return 0
  fi
  return 1
}

pm_update() {
  if [[ "${PM}" == "none" ]]; then
    return
  fi

  if [[ "${PM}" == "apt" ]]; then
    sudo apt-get update || true
    return
  fi
  if [[ "${PM}" == "dnf" ]]; then
    sudo dnf makecache || true
    return
  fi
  if [[ "${PM}" == "yum" ]]; then
    sudo yum makecache || true
    return
  fi
  if [[ "${PM}" == "zypper" ]]; then
    sudo zypper refresh || true
    return
  fi
  if [[ "${PM}" == "apk" ]]; then
    sudo apk update || true
    return
  fi
  if [[ "${PM}" == "brew" ]]; then
    brew update || true
    return
  fi
}

install_prereq_packages() {
  if [[ "${PM}" == "none" ]]; then
    echo "⚠️  Package manager not detected; skipping OS prereqs."
    return
  fi
  if ! sudo_available; then
    echo "⚠️  sudo not available; cannot install missing prerequisites."
    return
  fi
  pm_update

  if [[ "${PM}" == "apt" ]]; then
    if ! sudo apt-get install -y "$@"; then
      echo "⚠️  Failed to install prerequisites with apt-get." >&2
    fi
    return
  fi
  if [[ "${PM}" == "dnf" ]]; then
    if ! sudo dnf install -y "$@"; then
      echo "⚠️  Failed to install prerequisites with dnf." >&2
    fi
    return
  fi
  if [[ "${PM}" == "yum" ]]; then
    if ! sudo yum install -y "$@"; then
      echo "⚠️  Failed to install prerequisites with yum." >&2
    fi
    return
  fi
  if [[ "${PM}" == "zypper" ]]; then
    if ! sudo zypper install -y "$@"; then
      echo "⚠️  Failed to install prerequisites with zypper." >&2
    fi
    return
  fi
  if [[ "${PM}" == "apk" ]]; then
    if ! sudo apk add --no-cache "$@"; then
      echo "⚠️  Failed to install prerequisites with apk." >&2
    fi
    return
  fi
  if [[ "${PM}" == "brew" ]]; then
    if ! brew install "$@"; then
      echo "⚠️  Failed to install prerequisites with brew." >&2
    fi
    return
  fi
}

ensure_python() {
  if ! command -v python3 >/dev/null 2>&1; then
    echo "⚠️  python3 not found; attempting to install." >&2
    if [[ "${PM}" == "apt" ]]; then
      install_prereq_packages python3 python3-pip
    elif [[ "${PM}" == "dnf" || "${PM}" == "yum" ]]; then
      install_prereq_packages python3 python3-pip
    elif [[ "${PM}" == "zypper" ]]; then
      install_prereq_packages python3 python3-pip
    elif [[ "${PM}" == "apk" ]]; then
      install_prereq_packages python3 py3-pip
    elif [[ "${PM}" == "brew" ]]; then
      install_prereq_packages python
    fi
  fi
  if ! command -v python3 >/dev/null 2>&1; then
    echo "ERROR: python3 is required. Install Python 3.10+ and retry." >&2
    exit 1
  fi
  require_command python3
}

check_python_version() {
  python3 - <<'PYCODE'
import sys
if sys.version_info < (3, 10):
    raise SystemExit("ERROR: Python 3.10+ is required.")
PYCODE
}

ensure_git() {
  if ! command -v git >/dev/null 2>&1; then
    echo "⚠️  git not found; attempting to install." >&2
    if [[ "${PM}" == "apt" ]]; then
      install_prereq_packages git
    elif [[ "${PM}" == "dnf" || "${PM}" == "yum" || "${PM}" == "zypper" ]]; then
      install_prereq_packages git
    elif [[ "${PM}" == "apk" ]]; then
      install_prereq_packages git
    elif [[ "${PM}" == "brew" ]]; then
      install_prereq_packages git
    fi
  fi
  if ! command -v git >/dev/null 2>&1; then
    echo "ERROR: git is required. Install git and retry." >&2
    exit 1
  fi
  require_command git
}

ensure_venv_support() {
  if python3 -c "import venv" >/dev/null 2>&1 && python3 -c "import ensurepip" >/dev/null 2>&1; then
    return
  fi
  echo "⚠️  python3 venv support missing; attempting to install." >&2
  if [[ "${PM}" == "apt" ]]; then
    local py_minor
    py_minor="$(python3 - <<'PYCODE'
import sys
print(f"{sys.version_info[0]}.{sys.version_info[1]}")
PYCODE
)"
    if [[ "${py_minor}" != "" ]]; then
      install_prereq_packages "python${py_minor}-venv"
    fi
    install_prereq_packages python3-venv
  elif [[ "${PM}" == "dnf" || "${PM}" == "yum" ]]; then
    install_prereq_packages python3-virtualenv
  elif [[ "${PM}" == "zypper" ]]; then
    install_prereq_packages python3-virtualenv
  elif [[ "${PM}" == "apk" ]]; then
    install_prereq_packages py3-virtualenv
  elif [[ "${PM}" == "brew" ]]; then
    install_prereq_packages python
  fi
  if ! python3 -c "import venv" >/dev/null 2>&1 || ! python3 -c "import ensurepip" >/dev/null 2>&1; then
    echo "ERROR: python3 venv support is required but still unavailable." >&2
    exit 1
  fi
}

clean_previous_install() {
  echo "🧹 Cleaning previous install artifacts..."

  local remove_paths=(
    "${PROJECT_ROOT}/${VENV_DIR}"
    "${PROJECT_ROOT}/build"
    "${PROJECT_ROOT}/dist"
    "${PROJECT_ROOT}/.pytest_cache"
    "${PROJECT_ROOT}/.ruff_cache"
    "${PROJECT_ROOT}/.mypy_cache"
    "${PROJECT_ROOT}/.pyright"
    "${PROJECT_ROOT}/.coverage"
    "${PROJECT_ROOT}/htmlcov"
    "${PROJECT_ROOT}/test_reports"
  )

  for path in "${remove_paths[@]}"; do
    if [[ -e "${path}" ]]; then
      echo "🗑️  Removing ${path}"
      rm -rf "${path}"
    fi
  done

  find "${PROJECT_ROOT}" -maxdepth 2 -name "*.egg-info" -type d -print0 | while IFS= read -r -d '' item; do
    echo "🗑️  Removing ${item}"
    rm -rf "${item}"
  done

  echo "ℹ️  Preserving ${PROJECT_ROOT}/.data"
}

ensure_git_clean() {
  if [[ ! -d "${PROJECT_ROOT}/.git" ]]; then
    echo "ERROR: ${PROJECT_ROOT} is not a git repository; tag updates require git." >&2
    exit 1
  fi
  if ! git -C "${PROJECT_ROOT}" diff --quiet || ! git -C "${PROJECT_ROOT}" diff --cached --quiet; then
    echo "ERROR: Working tree is not clean; commit or stash changes before updating." >&2
    exit 1
  fi
  git -C "${PROJECT_ROOT}" fetch --tags
}

resolve_tag_version() {
  local tag_value="$1"
  if [[ "${tag_value}" == v* ]]; then
    echo "${tag_value#v}"
  else
    echo "${tag_value}"
  fi
}

select_latest_tag() {
  local selector="$1"
  local tags
  local filtered

  tags="$(git -C "${PROJECT_ROOT}" tag --list "v*")"
  if [[ "${tags}" == "" ]]; then
    echo ""
    return
  fi

  filtered="$(echo "${tags}" | while IFS= read -r tag; do
    value="${tag#v}"
    IFS='.' read -r major minor patch build <<<"${value}"
    if [[ "${major}" == "" || "${minor}" == "" || "${patch}" == "" || "${build}" == "" ]]; then
      continue
    fi
    case "${selector}" in
      ga)
        if [[ "${build}" == "0" ]]; then
          echo "${tag}"
        fi
        ;;
      hotfix)
        if [[ "${build}" != "0" ]]; then
          echo "${tag}"
        fi
        ;;
    esac
  done)"

  if [[ "${filtered}" == "" ]]; then
    echo ""
    return
  fi

  echo "${filtered}" | sort -V | tail -n 1
}

ensure_git_tag() {
  local tag_value="$1"
  if ! git -C "${PROJECT_ROOT}" rev-parse "${tag_value}" >/dev/null 2>&1; then
    echo "ERROR: Tag not found: ${tag_value}" >&2
    exit 1
  fi
}

ensure_venv() {
  if [[ ! -d "${VENV_DIR}" ]]; then
    python3 -m venv "${VENV_DIR}"
  fi
}

ensure_safe_pythonpath() {
  local allowed_src
  local entry

  if [[ "${PYTHONPATH:-}" == "" ]]; then
    return
  fi

  allowed_src="${PROJECT_ROOT}/src"
  IFS=':' read -r -a pythonpath_entries <<<"${PYTHONPATH}"
  for entry in "${pythonpath_entries[@]}"; do
    if [[ "${entry}" == "" ]]; then
      continue
    fi
    if [[ "${entry}" == "${allowed_src}" ]]; then
      continue
    fi
    echo "ERROR: PYTHONPATH is set to an external source path: ${entry}" >&2
    echo "This can cause PyPNM-CMTS to import a different pypnm runtime than the one installed in ${VENV_DIR}." >&2
    echo "Please run 'unset PYTHONPATH' and restart the install from a clean shell." >&2
    exit 1
  done
}

activate_venv() {
  # shellcheck source=/dev/null
  source "${VENV_DIR}/bin/activate"
}

verify_installed_runtime_paths() {
  local expected_venv_root
  local import_path
  local config_path
  local runtime_output

  if [[ "${VENV_DIR}" = /* ]]; then
    expected_venv_root="${VENV_DIR}"
  else
    expected_venv_root="${PROJECT_ROOT}/${VENV_DIR}"
  fi
  if [[ -e "${expected_venv_root}" ]]; then
    expected_venv_root="$(cd "${expected_venv_root}" && pwd -P)"
  fi

  if [[ "${PYPNM_CMTS_INSTALL_TEST_RUNTIME_IMPORT_PATH:-}" != "" || "${PYPNM_CMTS_INSTALL_TEST_RUNTIME_CONFIG_PATH:-}" != "" ]]; then
    import_path="${PYPNM_CMTS_INSTALL_TEST_RUNTIME_IMPORT_PATH:-}"
    config_path="${PYPNM_CMTS_INSTALL_TEST_RUNTIME_CONFIG_PATH:-}"
  else
    runtime_output="$(python - <<'PYCODE'
import pypnm
from pypnm.config.system_config_settings import SystemConfigSettings

print(pypnm.__file__)
print(SystemConfigSettings.get_config_path())
PYCODE
)"
    import_path="$(printf '%s\n' "${runtime_output}" | sed -n '1p')"
    config_path="$(printf '%s\n' "${runtime_output}" | sed -n '2p')"
  fi

  if [[ "${import_path}" != "${expected_venv_root}"/* ]]; then
    echo "ERROR: Installed runtime import check failed." >&2
    echo "pypnm imported from: ${import_path}" >&2
    echo "Expected under: ${expected_venv_root}" >&2
    echo "Check for leaked PYTHONPATH or another active source checkout." >&2
    exit 1
  fi

  if [[ "${config_path}" != "${expected_venv_root}"/* ]]; then
    echo "ERROR: Installed runtime config check failed." >&2
    echo "pypnm config resolved to: ${config_path}" >&2
    echo "Expected under: ${expected_venv_root}" >&2
    echo "Check for leaked PYTHONPATH or another active source checkout." >&2
    exit 1
  fi
}

purge_pip_cache() {
  if [[ "${PURGE_CACHE}" == "1" ]]; then
    python -m pip cache purge
  fi
}

install_dev_prereqs() {
  if [[ "${DEVELOPMENT_MODE}" != "1" ]]; then
    return
  fi
  install_gitleaks
}

install_gitleaks() {
  if command -v gitleaks >/dev/null 2>&1; then
    echo "✅ gitleaks already installed."
    return
  fi

  if [[ "${PM}" == "none" ]]; then
    echo "⚠️  gitleaks not found and no package manager available."
    echo "    Install manually: https://github.com/gitleaks/gitleaks"
    return
  fi

  echo "🔧 Installing gitleaks..."
  if [[ "${PM}" == "apt" ]]; then
    install_prereq_packages gitleaks
  elif [[ "${PM}" == "dnf" || "${PM}" == "yum" ]]; then
    install_prereq_packages gitleaks
  elif [[ "${PM}" == "zypper" ]]; then
    install_prereq_packages gitleaks
  elif [[ "${PM}" == "apk" ]]; then
    install_prereq_packages gitleaks
  elif [[ "${PM}" == "brew" ]]; then
    install_prereq_packages gitleaks
  else
    echo "⚠️  Unknown package manager; install gitleaks manually."
    echo "    https://github.com/gitleaks/gitleaks"
    return
  fi

  if command -v gitleaks >/dev/null 2>&1; then
    return
  fi
  if ! command -v curl >/dev/null 2>&1; then
    echo "⚠️  gitleaks install did not complete (curl missing)."
    echo "    Install manually: https://github.com/gitleaks/gitleaks"
    return
  fi
  if ! command -v tar >/dev/null 2>&1; then
    echo "⚠️  gitleaks install did not complete (tar missing)."
    echo "    Install manually: https://github.com/gitleaks/gitleaks"
    return
  fi

  local os arch filename url tmp_dir target_dir bin_path
  os="$(uname -s | tr '[:upper:]' '[:lower:]')"
  case "${os}" in
    linux|darwin) ;;
    *)
      echo "⚠️  Unsupported OS for gitleaks auto-install: ${os}"
      echo "    Install manually: https://github.com/gitleaks/gitleaks"
      return
      ;;
  esac

  arch="$(uname -m)"
  case "${arch}" in
    x86_64|amd64) arch="x64" ;;
    aarch64|arm64) arch="arm64" ;;
    *)
      echo "⚠️  Unsupported architecture for gitleaks auto-install: ${arch}"
      echo "    Install manually: https://github.com/gitleaks/gitleaks"
      return
      ;;
  esac

  filename="gitleaks_${GITLEAKS_VERSION}_${os}_${arch}.tar.gz"
  url="https://github.com/gitleaks/gitleaks/releases/download/v${GITLEAKS_VERSION}/${filename}"
  tmp_dir="$(mktemp -d)"
  echo "⬇️  Downloading gitleaks ${GITLEAKS_VERSION}..."
  if ! curl -fsSL "${url}" -o "${tmp_dir}/${filename}"; then
    echo "⚠️  Failed to download gitleaks from ${url}"
    echo "    Install manually: https://github.com/gitleaks/gitleaks"
    rm -rf "${tmp_dir}"
    return
  fi

  if ! tar -xzf "${tmp_dir}/${filename}" -C "${tmp_dir}"; then
    echo "⚠️  Failed to extract gitleaks archive."
    echo "    Install manually: https://github.com/gitleaks/gitleaks"
    rm -rf "${tmp_dir}"
    return
  fi

  bin_path="${tmp_dir}/gitleaks"
  if [[ ! -f "${bin_path}" ]]; then
    echo "⚠️  gitleaks binary not found after extraction."
    echo "    Install manually: https://github.com/gitleaks/gitleaks"
    rm -rf "${tmp_dir}"
    return
  fi

  target_dir="/usr/local/bin"
  if [[ -w "${target_dir}" ]]; then
    install -m 0755 "${bin_path}" "${target_dir}/gitleaks"
  elif command -v sudo >/dev/null 2>&1; then
    sudo install -m 0755 "${bin_path}" "${target_dir}/gitleaks"
  else
    target_dir="${HOME}/.local/bin"
    mkdir -p "${target_dir}"
    install -m 0755 "${bin_path}" "${target_dir}/gitleaks"
    echo "ℹ️  Added gitleaks to ${target_dir}; ensure it's on PATH."
  fi

  rm -rf "${tmp_dir}"
  if ! command -v gitleaks >/dev/null 2>&1; then
    echo "⚠️  gitleaks install did not complete."
    echo "    Install manually: https://github.com/gitleaks/gitleaks"
    return
  fi
}

install_standard() {
  ensure_venv
  activate_venv
  python -m pip install --upgrade pip setuptools wheel
  purge_pip_cache
  if python -m pip install -e "${PROJECT_ROOT}[dev,docs]"; then
    return
  fi
  echo "⚠️  Install with [dev,docs] failed; falling back to [dev]." >&2
  if python -m pip install -e "${PROJECT_ROOT}[dev]"; then
    python -m pip install pytest mkdocs mkdocs-material mkdocs-mermaid2-plugin pymdown-extensions
    return
  fi
  echo "⚠️  Install with [dev] failed; falling back to base install." >&2
  python -m pip install -e "${PROJECT_ROOT}"
  python -m pip install pytest mkdocs mkdocs-material mkdocs-mermaid2-plugin pymdown-extensions
}

install_from_tag() {
  local tag_value="$1"
  local label="$2"
  local version_value
  local worktree_dir
  local cleanup_done

  if [[ "${tag_value}" == "" ]]; then
    if [[ "${label}" == "GA" ]]; then
      tag_value="$(select_latest_tag ga)"
    else
      tag_value="$(select_latest_tag hotfix)"
    fi
  fi
  if [[ "${tag_value}" == "" ]]; then
    echo "ERROR: No matching tags found for ${label} update." >&2
    exit 1
  fi

  ensure_git_tag "${tag_value}"
  version_value="$(resolve_tag_version "${tag_value}")"

  echo "✅ Updating to ${label} tag ${tag_value}"
  worktree_dir="$(mktemp -d)"
  cleanup_done="0"

  cleanup_worktree() {
    if [[ "${cleanup_done}" == "1" ]]; then
      return
    fi
    cleanup_done="1"
    git -C "${PROJECT_ROOT}" worktree remove --force "${worktree_dir}" >/dev/null 2>&1 || true
    rm -rf "${worktree_dir}" >/dev/null 2>&1 || true
  }

  trap cleanup_worktree EXIT
  git -C "${PROJECT_ROOT}" worktree add --detach "${worktree_dir}" "${tag_value}"

  ensure_venv
  activate_venv
  python -m pip install --upgrade pip setuptools wheel
  purge_pip_cache
  python -m pip install --upgrade --force-reinstall "${worktree_dir}"
  python - <<PYCODE
import pypnm_cmts
version = pypnm_cmts.__version__
if version != "${version_value}":
    raise SystemExit(f"Installed version {version} does not match tag ${tag_value}")
print(f"Installed PyPNM-CMTS v{version}")
PYCODE

  cleanup_worktree
  trap - EXIT
}

ensure_no_running_pypnm_cmts_serve() {
  local running
  local kill_script
  running="$(pgrep -af '[p]ypnm-cmts serve' || true)"
  if [[ "${running}" != "" ]]; then
    kill_script="${PROJECT_ROOT}/tools/maintenance/kill-pypnm-cmts.py"
    echo "ERROR: pypnm-cmts serve is currently running." >&2
    echo "${running}" >&2
    if [[ -f "${kill_script}" ]]; then
      echo "Run: python3 ${kill_script} --all" >&2
    fi
    echo "Please stop pypnm-cmts serve before running --update-development-pypnm-docsis." >&2
    exit 1
  fi
}

install_update_development_pypnm_docsis() {
  ensure_no_running_pypnm_cmts_serve
  ensure_venv
  activate_venv
  python -m pip install --upgrade pip setuptools wheel
  purge_pip_cache
  local current_version
  local target_version
  local install_spec
  local confirm

  current_version="$(python - <<'PYCODE'
from importlib.metadata import PackageNotFoundError, version
try:
    print(version("pypnm-docsis"))
except PackageNotFoundError:
    print("not-installed")
PYCODE
)"

  if [[ "${UPDATE_DEVELOPMENT_PYPNM_DOCSIS_TAG}" != "" ]]; then
    target_version="${UPDATE_DEVELOPMENT_PYPNM_DOCSIS_TAG#v}"
    install_spec="pypnm-docsis==${target_version}"
  else
    target_version="$(python -m pip index versions pypnm-docsis --pre 2>/dev/null | sed -n 's/^Available versions: //p' | head -n 1 | cut -d',' -f1 | tr -d ' ')"
    if [[ "${target_version}" == "" ]]; then
      target_version="latest pre-release"
    fi
    install_spec="pypnm-docsis"
  fi

  echo "pypnm-docsis local version: ${current_version}"
  echo "pypnm-docsis target version: ${target_version}"
  read -r -p "Proceed with update to ${target_version}? [y/N]: " confirm
  case "${confirm}" in
    y|Y|yes|YES)
      ;;
    *)
      echo "Cancelled pypnm-docsis update."
      exit 0
      ;;
  esac

  if [[ "${UPDATE_DEVELOPMENT_PYPNM_DOCSIS_TAG}" != "" ]]; then
    python -m pip install --upgrade "${install_spec}"
  else
    python -m pip install --upgrade --pre "${install_spec}"
  fi
  python - <<'PYCODE'
import pypnm
print(f"Installed pypnm-docsis v{pypnm.__version__}")
PYCODE
}

verify_mkdocs() {
  if ! python -m mkdocs --version >/dev/null 2>&1; then
    echo "ERROR: mkdocs is not available; ensure docs extras are installed." >&2
    exit 1
  fi
  python -m mkdocs --version
}

run_tests() {
  if [[ ! -d "${PROJECT_ROOT}/tests" ]]; then
    echo "⚠️  tests directory not found; skipping pytest."
    return
  fi
  (cd "${PROJECT_ROOT}" && python -m pytest -v)
}

resolve_system_config_path_from_python() {
  local python_bin="$1"
  if [[ ! -x "${python_bin}" ]]; then
    return
  fi
  "${python_bin}" - <<'PYCODE' 2>/dev/null || true
from pypnm.config.system_config_settings import SystemConfigSettings
print(SystemConfigSettings.get_config_path())
PYCODE
}

resolve_existing_system_config_path() {
  local path_candidate=""

  path_candidate="$(resolve_system_config_path_from_python "${PROJECT_ROOT}/${VENV_DIR}/bin/python" | tail -n 1)"
  if [[ "${path_candidate}" != "" && -f "${path_candidate}" ]]; then
    echo "${path_candidate}"
    return
  fi

  path_candidate="${PROJECT_ROOT}/.data/system.json"
  if [[ -f "${path_candidate}" ]]; then
    echo "${path_candidate}"
    return
  fi
}

resolve_install_target_system_config_path() {
  local path_candidate=""
  path_candidate="$(resolve_system_config_path_from_python "${PROJECT_ROOT}/${VENV_DIR}/bin/python" | tail -n 1)"
  if [[ "${path_candidate}" != "" ]]; then
    echo "${path_candidate}"
    return
  fi
  echo "${PROJECT_ROOT}/.data/system.json"
}

prepare_system_config_carry_over() {
  local existing_path
  local carry_answer

  existing_path="$(resolve_existing_system_config_path)"
  if [[ "${existing_path}" == "" ]]; then
    return
  fi

  PREVIOUS_SYSTEM_CONFIG_PATH="${existing_path}"
  echo "⚠️  Previous installation detected."
  echo "⚠️  This install can overwrite runtime configuration files."
  echo "Detected existing system config: ${PREVIOUS_SYSTEM_CONFIG_PATH}"

  if [[ -t 0 ]]; then
    read -r -p "Carry over existing system config after install? [Y/n]: " carry_answer
  else
    carry_answer="y"
    echo "ℹ️  Non-interactive shell detected; defaulting to carry-over: yes."
  fi

  case "${carry_answer}" in
    ""|y|Y|yes|YES)
      SYSTEM_CONFIG_BACKUP_FILE="$(mktemp)"
      cp "${PREVIOUS_SYSTEM_CONFIG_PATH}" "${SYSTEM_CONFIG_BACKUP_FILE}"
      RESTORE_SYSTEM_CONFIG_AFTER_INSTALL="1"
      echo "✅ Backed up existing system config for post-install restore."
      ;;
    *)
      RESTORE_SYSTEM_CONFIG_AFTER_INSTALL="0"
      echo "ℹ️  Continuing without carrying over existing system config."
      ;;
  esac
}

restore_carried_system_config() {
  local target_path=""
  if [[ "${RESTORE_SYSTEM_CONFIG_AFTER_INSTALL}" != "1" ]]; then
    return
  fi
  if [[ "${SYSTEM_CONFIG_BACKUP_FILE}" == "" || ! -f "${SYSTEM_CONFIG_BACKUP_FILE}" ]]; then
    return
  fi

  target_path="$(resolve_install_target_system_config_path)"
  if [[ "${target_path}" == "" ]]; then
    target_path="${PREVIOUS_SYSTEM_CONFIG_PATH}"
  fi
  if [[ "${target_path}" == "" ]]; then
    target_path="${PROJECT_ROOT}/.data/system.json"
  fi

  mkdir -p "$(dirname "${target_path}")"
  cp "${SYSTEM_CONFIG_BACKUP_FILE}" "${target_path}"
  rm -f "${SYSTEM_CONFIG_BACKUP_FILE}"
  SYSTEM_CONFIG_BACKUP_FILE=""
  echo "✅ Restored carried-over system config to: ${target_path}"
}

if [[ $# -eq 0 ]]; then
  MODE="standard"
else
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --development)
        DEVELOPMENT_MODE="1"
        MODE="development"
        shift
        ;;
      --update-ga)
        UPDATE_GA_MODE="1"
        MODE="update-ga"
        UPDATE_TAG="${2:-}"
        if [[ "${UPDATE_TAG}" != "" && "${UPDATE_TAG}" != --* ]]; then
          shift 2
        else
          UPDATE_TAG=""
          shift
        fi
        ;;
      --update-hot-fix)
        UPDATE_HOT_FIX_MODE="1"
        MODE="update-hot-fix"
        UPDATE_TAG="${2:-}"
        if [[ "${UPDATE_TAG}" != "" && "${UPDATE_TAG}" != --* ]]; then
          shift 2
        else
          UPDATE_TAG=""
          shift
        fi
        ;;
      --update-development-pypnm-docsis)
        UPDATE_DEVELOPMENT_PYPNM_DOCSIS_MODE="1"
        MODE="update-development-pypnm-docsis"
        UPDATE_DEVELOPMENT_PYPNM_DOCSIS_TAG="${2:-}"
        if [[ "${UPDATE_DEVELOPMENT_PYPNM_DOCSIS_TAG}" != "" && "${UPDATE_DEVELOPMENT_PYPNM_DOCSIS_TAG}" != --* ]]; then
          shift 2
        else
          UPDATE_DEVELOPMENT_PYPNM_DOCSIS_TAG=""
          shift
        fi
        ;;
      --clean)
        CLEAN_MODE="1"
        shift
        ;;
      --purge-cache)
        PURGE_CACHE="1"
        shift
        ;;
      --uninstall)
        UNINSTALL_MODE="1"
        MODE="uninstall"
        shift
        ;;
      --help|-h)
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
        VENV_DIR="$1"
        shift
        ;;
    esac
  done
fi

if [[ "${UNINSTALL_MODE}" == "1" ]]; then
  if [[ "${CLEAN_MODE}" == "1" || "${DEVELOPMENT_MODE}" == "1" || "${UPDATE_GA_MODE}" == "1" || "${UPDATE_HOT_FIX_MODE}" == "1" || "${UPDATE_DEVELOPMENT_PYPNM_DOCSIS_MODE}" == "1" ]]; then
    echo "ERROR: --uninstall cannot be combined with other flags." >&2
    usage
    exit 1
  fi
fi

if [[ "${PYPNM_CMTS_INSTALL_TEST:-}" == "1" ]]; then
  echo "PYPNM_CMTS_INSTALL_TEST_MODE=${MODE}"
  echo "PYPNM_CMTS_INSTALL_TEST_VENV_DIR=${VENV_DIR}"
  if [[ "${PYPNM_CMTS_INSTALL_TEST_REPORT_PYTHONPATH:-}" == "1" ]]; then
    if [[ "${PYTHONPATH:-}" == "" ]]; then
      echo "PYPNM_CMTS_INSTALL_TEST_PYTHONPATH_OK=1"
    else
      set +e
      ensure_safe_pythonpath
      status=$?
      set -e
      echo "PYPNM_CMTS_INSTALL_TEST_PYTHONPATH_STATUS=${status}"
    fi
  fi
  if [[ "${PYPNM_CMTS_INSTALL_TEST_REPORT_RUNTIME_CHECK:-}" == "1" ]]; then
    set +e
    verify_installed_runtime_paths
    status=$?
    set -e
    echo "PYPNM_CMTS_INSTALL_TEST_RUNTIME_CHECK_STATUS=${status}"
  fi
  if [[ "${UPDATE_DEVELOPMENT_PYPNM_DOCSIS_TAG}" != "" ]]; then
    echo "PYPNM_CMTS_INSTALL_TEST_PYPNM_DOCSIS_TAG=${UPDATE_DEVELOPMENT_PYPNM_DOCSIS_TAG}"
  fi
  if [[ "${PYPNM_CMTS_INSTALL_TEST_CREATE_VENV:-}" == "1" ]]; then
    python3 -m venv "${VENV_DIR}"
    rm -rf "${VENV_DIR}"
  fi
  exit 0
fi

detect_package_manager
if [[ "${PM}" != "none" ]]; then
  echo "ℹ️  Detected package manager: ${PM}"
else
  echo "ℹ️  No package manager detected."
fi

print_banner
ensure_safe_pythonpath
ensure_python
check_python_version
ensure_git
ensure_venv_support
if [[ "${MODE}" == "standard" || "${MODE}" == "development" || "${MODE}" == "update-ga" || "${MODE}" == "update-hot-fix" ]]; then
  prepare_system_config_carry_over
fi

if [[ "${CLEAN_MODE}" == "1" || "${UNINSTALL_MODE}" == "1" ]]; then
  clean_previous_install
fi

if [[ "${UNINSTALL_MODE}" == "1" ]]; then
  echo "✅ Uninstall complete."
  exit 0
fi

install_dev_prereqs

if [[ "${MODE}" == "standard" || "${MODE}" == "development" ]]; then
  install_standard
else
  if [[ "${MODE}" == "update-development-pypnm-docsis" ]]; then
    install_update_development_pypnm_docsis
  else
    ensure_git_clean
    if [[ "${MODE}" == "update-ga" ]]; then
      install_from_tag "${UPDATE_TAG}" "GA"
    else
      install_from_tag "${UPDATE_TAG}" "hot-fix"
    fi
  fi
fi
restore_carried_system_config

verify_installed_runtime_paths
verify_mkdocs
run_tests

echo "Next steps:"
echo "  source ${VENV_DIR}/bin/activate"
echo "  pypnm-cmts serve --help"
echo "  mkdocs serve -a 127.0.0.1:8081"
