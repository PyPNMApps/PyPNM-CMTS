#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Scan the repository for potential secrets using gitleaks (if available)
# and basic heuristic checks as a fallback.

set -euo pipefail
IFS=$'\n\t'

usage() {
  cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Scan the current Git repository for potential secrets.

Options:
  --all-history    Scan full Git history (gitleaks only). Default: working tree.
  --path DIR       Repository root (default: project root inferred from this script).
  -h, --help       Show this help message and exit.

Exit codes:
  0  No issues detected.
  1  Errors running the scanner.
  2  Potential secrets detected.
EOF
}

SCAN_ALL_HISTORY=0
CUSTOM_PATH=""

while [ "$#" -gt 0 ]; do
  case "$1" in
    --all-history)
      SCAN_ALL_HISTORY=1
      shift
      ;;
    --path)
      if [ "$#" -lt 2 ]; then
        echo "ERROR: --path requires a directory." >&2
        exit 1
      fi
      CUSTOM_PATH="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "ERROR: Unknown argument: $1" >&2
      usage
      exit 1
      ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT_DEFAULT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
PROJECT_ROOT="${CUSTOM_PATH:-${PROJECT_ROOT_DEFAULT}}"

if [ ! -d "${PROJECT_ROOT}/.git" ]; then
  echo "ERROR: ${PROJECT_ROOT} does not look like a Git repository (.git missing)." >&2
  exit 1
fi

cd "${PROJECT_ROOT}"

echo "Project root      : ${PROJECT_ROOT}"
echo "Scan full history : ${SCAN_ALL_HISTORY}"

has_gitleaks=0
if command -v gitleaks >/dev/null 2>&1; then
  has_gitleaks=1
fi

if [ "${has_gitleaks}" -eq 1 ]; then
  echo "Using gitleaks for secret scanning..."

  cmd=(gitleaks detect --source "${PROJECT_ROOT}" --no-banner --redact)

  if [ "${SCAN_ALL_HISTORY}" -eq 1 ]; then
    cmd+=(--log-opts=--all)
  fi

  echo "Running: ${cmd[*]}"
  if "${cmd[@]}"; then
    echo "gitleaks reported no secrets."
    exit 0
  else
    status=$?
    if [ "${status}" -eq 1 ]; then
      echo "gitleaks detected potential secrets."
      exit 2
    fi
    echo "ERROR: gitleaks exited with status ${status}."
    exit 1
  fi
fi

echo "WARNING: gitleaks not found; falling back to heuristic scan."
echo "Install gitleaks for stronger checks: https://github.com/gitleaks/gitleaks"

REGEX_PATTERNS=(
  "AKIA[0-9A-Z]{16}"
  "ASIA[0-9A-Z]{16}"
  "AWS_ACCESS_KEY_ID[\"'=:\\s]+[A-Z0-9]{16,}"
  "AWS_SECRET_ACCESS_KEY[\"'=:\\s]+[A-Za-z0-9/+=]{20,}"
  "-----BEGIN[[:space:]]+(RSA|OPENSSH|EC|DSA)?[[:space:]]*PRIVATE KEY-----"
  "xox[baprs]-[A-Za-z0-9-]{10,}"
  "ghp_[A-Za-z0-9]{20,}"
  "github_pat_[A-Za-z0-9_]{20,}"
  "pypi-[A-Za-z0-9]{20,}"
  "access[_-]?token[\"'=:\\s]+[A-Za-z0-9/_-]{10,}"
  "secret[_-]?key[\"'=:\\s]+[A-Za-z0-9/_-]{10,}"
)

EXCLUDE_PATHS=(
  ":(exclude)tools/security/scan-secrets.sh"
  ":(exclude)docs/system/pnm-file-retrieval/scp-key-setup-helper.md"
  ":(exclude)docs/system/pnm-file-retrieval/sftp.md"
  ":(exclude)docs/system/pnm-file-retrieval/ssh_file_retrieval_setup.md"
  ":(exclude)deploy/docker/compose/.env.example"
)

FOUND=0
WARNED=0

for pattern in "${REGEX_PATTERNS[@]}"; do
  if git grep -n -E --ignore-case -- "${pattern}" -- . "${EXCLUDE_PATHS[@]}" >/dev/null 2>&1; then
    if [ "${FOUND}" -eq 0 ]; then
      echo "Potential secrets found by heuristic scan:"
    fi
    FOUND=2
    git grep -n -E --ignore-case -- "${pattern}" -- . "${EXCLUDE_PATHS[@]}" || true
  fi

  if git grep -n -E --ignore-case -- "${pattern}" -- \
      "tools/security/scan-secrets.sh" \
      "docs/system/pnm-file-retrieval/scp-key-setup-helper.md" \
      "docs/system/pnm-file-retrieval/sftp.md" \
      "docs/system/pnm-file-retrieval/ssh_file_retrieval_setup.md" \
      "deploy/docker/compose/.env.example" >/dev/null 2>&1; then
    if [ "${WARNED}" -eq 0 ]; then
      echo "WARNING: Potential secret-like strings found in allowlisted examples/docs:"
    fi
    WARNED=1
    git grep -n -E --ignore-case -- "${pattern}" -- \
      "tools/security/scan-secrets.sh" \
      "docs/system/pnm-file-retrieval/scp-key-setup-helper.md" \
      "docs/system/pnm-file-retrieval/sftp.md" \
      "docs/system/pnm-file-retrieval/ssh_file_retrieval_setup.md" \
      "deploy/docker/compose/.env.example" || true
  fi
done

if [ "${FOUND}" -eq 0 ]; then
  echo "Heuristic scan did not find obvious secrets."
  exit 0
fi

exit "${FOUND}"
