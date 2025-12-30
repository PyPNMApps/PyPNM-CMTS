#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

set -euo pipefail
IFS=$'\n\t'

SCRIPT_NAME="$(basename "$0")"
DEFAULT_BASE_URL="http://127.0.0.1:8000"

usage() {
  cat <<EOF
Usage:
  ${SCRIPT_NAME} --base-url <url>

Options:
  --base-url <url>   Base URL for the service (default: ${DEFAULT_BASE_URL})
  -h, --help         Show this help and exit

Example:
  ${SCRIPT_NAME} --base-url http://127.0.0.1:8000
EOF
}

base_url="${DEFAULT_BASE_URL}"

while [[ "${#}" -gt 0 ]]; do
  case "$1" in
    --base-url)
      base_url="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "ERROR: Unknown argument: $1" 1>&2
      usage
      exit 2
      ;;
  esac
done

if [[ -z "${base_url}" ]]; then
  echo "ERROR: --base-url must be non-empty." 1>&2
  exit 2
fi

health_url="${base_url%/}/ops/health"

response="$(curl -sS -w "\n%{http_code}" "${health_url}")"
body="$(printf '%s' "${response}" | sed '$d')"
status_code="$(printf '%s' "${response}" | tail -n 1)"

if [[ "${status_code}" != "200" ]]; then
  echo "ERROR: /ops/health returned HTTP ${status_code}" 1>&2
  exit 1
fi

if ! printf '%s' "${body}" | grep -Eq '"status"[[:space:]]*:[[:space:]]*"ok"'; then
  echo "ERROR: /ops/health response did not include status ok" 1>&2
  exit 1
fi

echo "OK: /ops/health returned status ok"
