#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Stage and commit the current Git repository.

Usage:
  git-save.sh [--commit-msg "Message"] [--push] [--skip-ruff] [--ruff-fix]

Options:
  --commit-msg  Commit message prefix (default: "Update").
  --push        Push the current branch after commit.
  --skip-ruff   Skip ruff checks before committing.
  --ruff-fix    Run ruff with --fix before committing.
  -h, --help    Show this help.
EOF
}

commit_msg="Update"
do_push="false"
skip_ruff="false"
ruff_fix="false"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --commit-msg)
      shift
      if [[ "${1:-}" == "" ]]; then
        echo "ERROR: --commit-msg requires a value." >&2
        exit 1
      fi
      commit_msg="$1"
      shift
      ;;
    --push)
      do_push="true"
      shift
      ;;
    --skip-ruff)
      skip_ruff="true"
      shift
      ;;
    --ruff-fix)
      ruff_fix="true"
      shift
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

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "ERROR: This script must be run inside a Git repository." >&2
  exit 1
fi

repo_root="$(git rev-parse --show-toplevel)"
cd "${repo_root}"

current_branch="$(git rev-parse --abbrev-ref HEAD)"
pending_changes="$(git status --short)"

echo "========================================"
echo "Git Save"
echo "Branch: ${current_branch}"
echo "Changes:"
if [[ -z "${pending_changes}" ]]; then
  echo "  (none)"
else
  printf '%s\n' "${pending_changes}"
fi
echo "========================================"

timestamp="$(date +'%Y-%m-%d %H:%M:%S')"
final_msg="${commit_msg} - ${timestamp}"

if git diff --quiet && git diff --cached --quiet; then
  echo "No changes to commit."
  exit 0
fi

if [[ "${skip_ruff}" != "true" ]]; then
  if ! command -v ruff >/dev/null 2>&1; then
    echo "ERROR: ruff not found on PATH. Use --skip-ruff or install ruff." >&2
    exit 1
  fi
  echo "Running ruff checks..."
  if [[ "${ruff_fix}" == "true" ]]; then
    ruff check . --fix
  else
    ruff check .
  fi
fi

echo "Staging changes..."
git add -A

echo "Creating commit..."
git commit -m "${final_msg}"

if [[ "${do_push}" == "true" ]]; then
  remote_name="$(git config branch."${current_branch}".remote || true)"
  echo "Pushing to origin (${current_branch})..."
  if [[ -z "${remote_name}" ]]; then
    git push -u origin "${current_branch}"
  else
    git push "${remote_name}" "${current_branch}"
  fi
else
  echo "Push skipped. Use --push to push."
fi

echo "Done."
