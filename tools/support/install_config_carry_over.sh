#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia
set -euo pipefail

# This helper is sourced by install.sh to keep install orchestration lean.

PREVIOUS_SYSTEM_CONFIG_PATH="${PREVIOUS_SYSTEM_CONFIG_PATH:-}"
SYSTEM_CONFIG_BACKUP_FILE="${SYSTEM_CONFIG_BACKUP_FILE:-}"
RESTORE_SYSTEM_CONFIG_AFTER_INSTALL="${RESTORE_SYSTEM_CONFIG_AFTER_INSTALL:-0}"

_resolve_system_config_path_from_python() {
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
  local project_root="$1"
  local venv_dir="$2"
  local path_candidate=""

  path_candidate="$(_resolve_system_config_path_from_python "${project_root}/${venv_dir}/bin/python" | tail -n 1)"
  if [[ "${path_candidate}" != "" && -f "${path_candidate}" ]]; then
    echo "${path_candidate}"
    return
  fi

  path_candidate="${project_root}/.data/system.json"
  if [[ -f "${path_candidate}" ]]; then
    echo "${path_candidate}"
    return
  fi
}

resolve_install_target_system_config_path() {
  local project_root="$1"
  local venv_dir="$2"
  local path_candidate=""

  path_candidate="$(_resolve_system_config_path_from_python "${project_root}/${venv_dir}/bin/python" | tail -n 1)"
  if [[ "${path_candidate}" != "" ]]; then
    echo "${path_candidate}"
    return
  fi
  echo "${project_root}/.data/system.json"
}

prepare_system_config_carry_over() {
  local project_root="$1"
  local venv_dir="$2"
  local existing_path=""
  local carry_answer=""

  existing_path="$(resolve_existing_system_config_path "${project_root}" "${venv_dir}")"
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
  local project_root="$1"
  local venv_dir="$2"
  local target_path=""

  if [[ "${RESTORE_SYSTEM_CONFIG_AFTER_INSTALL}" != "1" ]]; then
    return
  fi
  if [[ "${SYSTEM_CONFIG_BACKUP_FILE}" == "" || ! -f "${SYSTEM_CONFIG_BACKUP_FILE}" ]]; then
    return
  fi

  target_path="$(resolve_install_target_system_config_path "${project_root}" "${venv_dir}")"
  if [[ "${target_path}" == "" ]]; then
    target_path="${PREVIOUS_SYSTEM_CONFIG_PATH}"
  fi
  if [[ "${target_path}" == "" ]]; then
    target_path="${project_root}/.data/system.json"
  fi

  mkdir -p "$(dirname "${target_path}")"
  cp "${SYSTEM_CONFIG_BACKUP_FILE}" "${target_path}"
  rm -f "${SYSTEM_CONFIG_BACKUP_FILE}"
  SYSTEM_CONFIG_BACKUP_FILE=""
  echo "✅ Restored carried-over system config to: ${target_path}"
}
