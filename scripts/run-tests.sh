#!/usr/bin/env sh
# POSIX-safe test runner for PyPNM-CMTS
# Usage: ./scripts/run-tests.sh [pytest-args]
set -eu

if [ "${VIRTUAL_ENV:-}" = "" ]; then
  echo "Warning: virtualenv not detected (VIRTUAL_ENV unset). Recommended: create and activate a venv."
fi

PYTHON="$(command -v python 2>/dev/null || command -v python3 2>/dev/null || true)"

if [ -z "$PYTHON" ]; then
  echo "python executable not found"
  exit 1
fi

printf "Enforcing Python 3.10+...\n"
"$PYTHON" - <<'PY'
import sys
if sys.version_info < (3, 10):
    sys.exit("Python 3.10+ is required; found {}.{}.{}.".format(*sys.version_info[:3]))
print(f"Python {sys.version_info[0]}.{sys.version_info[1]} detected.")
PY

LOG_DIR="logs"
BACKUP=""
SYMLINK_TARGET=""

restore_logs() {
  if [ -n "$SYMLINK_TARGET" ]; then
    rm -rf "$LOG_DIR"
    ln -s "$SYMLINK_TARGET" "$LOG_DIR"
  elif [ -n "$BACKUP" ] && [ -e "$BACKUP" ]; then
    if [ -e "$LOG_DIR" ]; then
      rm -rf "$LOG_DIR"
    fi
    mv "$BACKUP" "$LOG_DIR"
  fi
}
trap restore_logs EXIT

backup_logs() {
  if [ -L "$LOG_DIR" ]; then
    SYMLINK_TARGET="$(readlink "$LOG_DIR")"
    rm "$LOG_DIR"
    BACKUP=""
  elif [ -e "$LOG_DIR" ]; then
    BACKUP="${LOG_DIR}.backup.$$"
    mv "$LOG_DIR" "$BACKUP"
  fi
}

remove_logs_if_present() {
  if [ -e "$LOG_DIR" ] || [ -L "$LOG_DIR" ]; then
    rm -rf "$LOG_DIR"
  fi
}

# Ensure logs are absent during install/setup
backup_logs
printf "Installing package and test extras...\n"
"$PYTHON" -m pip install -U pip setuptools wheel
"$PYTHON" -m pip install -e ".[test]"

remove_logs_if_present

mkdir -p "$LOG_DIR"

printf "Running pytest via python -m pytest...\n"
"$PYTHON" -m pytest "$@"
