#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

_repo_root() {
  git rev-parse --show-toplevel 2>/dev/null
}

_now_utc_compact() {
  date -u +"%Y%m%dT%H%M%SZ"
}

_have_cmd() {
  command -v "$1" >/dev/null 2>&1
}

_print() {
  if [[ "${BUNDLE_QUIET:-0}" -eq 1 ]]; then
    return 0
  fi
  printf '%s\n' "$*"
}

_warn() {
  if [[ "${BUNDLE_QUIET:-0}" -eq 1 ]]; then
    return 0
  fi
  printf 'WARN: %s\n' "$*" >&2
}

_die() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 2
}

_usage() {
  cat <<'EOF'
Usage: development/support/bundle.sh [OPTIONS]

Creates a support bundle directory under development/bundles/ by default.
Optionally creates a tar.gz with --tar.

Options:
  --out-dir DIR           Output directory (default: <repo>/development/bundles)
  --name NAME             Base bundle name (default: support-bundle)
  --no-modified           Do not auto-include modified/staged files
  --no-untracked          Do not auto-include untracked files
  --add FILE              Add an extra file (repeatable)
  --tar                   Also create a tar.gz alongside the directory
  --quiet                 Minimal output
  -h, --help              Show help

Examples:
  ./development/bundle.sh
  ./development/bundle.sh --name phase-6.5-step-4
  ./development/bundle.sh --add mode-contract.md --add review-bundle.txt
  ./development/bundle.sh --no-untracked
  ./development/bundle.sh --tar
EOF
}

_copy_one() {
  local repo_root="$1"
  local stage_dir="$2"
  local rel="$3"

  if [[ -z "${rel}" ]]; then
    return 0
  fi

  local src="${repo_root}/${rel}"
  if [[ ! -e "${src}" ]]; then
    _warn "Missing: ${rel}"
    return 0
  fi

  local dst_dir="${stage_dir}/files/$(dirname "${rel}")"
  mkdir -p "${dst_dir}"

  if [[ -d "${src}" ]]; then
    if _have_cmd rsync; then
      rsync -a "${src}/" "${dst_dir}/$(basename "${rel}")/"
    else
      cp -a "${src}" "${dst_dir}/"
    fi
  else
    cp -a "${src}" "${dst_dir}/"
  fi
}

_write_text_file() {
  local out="$1"
  shift
  {
    for line in "$@"; do
      printf '%s\n' "${line}"
    done
  } > "${out}"
}

_git_list_modified() {
  git diff --name-only
}

_git_list_staged() {
  git diff --cached --name-only
}

_git_list_untracked() {
  git ls-files --others --exclude-standard
}

_main() {
  local repo_root
  repo_root="$(_repo_root)"
  if [[ -z "${repo_root}" ]]; then
    _die "Not a git repository (or git not available). Run from within the repo."
  fi

  local out_dir="${repo_root}/development/bundles"
  local name="support-bundle"
  local include_modified=1
  local include_untracked=1
  local make_tar=0
  local -a extra_files=()

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --out-dir)
        shift
        [[ $# -gt 0 ]] || _die "--out-dir requires a value"
        out_dir="$1"
        ;;
      --name)
        shift
        [[ $# -gt 0 ]] || _die "--name requires a value"
        name="$1"
        ;;
      --no-modified)
        include_modified=0
        ;;
      --no-untracked)
        include_untracked=0
        ;;
      --add)
        shift
        [[ $# -gt 0 ]] || _die "--add requires a value"
        extra_files+=("$1")
        ;;
      --tar)
        make_tar=1
        ;;
      --quiet)
        export BUNDLE_QUIET=1
        ;;
      -h|--help)
        _usage
        return 0
        ;;
      *)
        _die "Unknown option: $1 (use --help)"
        ;;
    esac
    shift
  done

  mkdir -p "${out_dir}"

  local ts
  ts="$(_now_utc_compact)"
  local bundle_base="${name}-${ts}"
  local bundle_dir="${out_dir}/${bundle_base}"

  _print "Support Bundle"
  _print "  Repo: ${repo_root}"
  _print "  Out : ${bundle_dir}"

  if [[ -e "${bundle_dir}" ]]; then
    _die "Output already exists: ${bundle_dir}"
  fi

  mkdir -p "${bundle_dir}/meta"
  mkdir -p "${bundle_dir}/files"

  # Default “always useful” set (safe to skip if not present)
  local -a defaults=(
    "mode-contract.md"
    "review-bundle.txt"
    "phase-6.5-step-3-20251231.txt"
    "phase-6.5-step-4-20251231.txt"
    "src/pypnm_cmts/orchestrator/launcher.py"
    "tests/test_orchestrator_launcher.py"
    "src/pypnm_cmts/cli.py"
    "docs/cli.md"
    "development/support/bundle.sh"
    "development/bundle.sh"
    "pyproject.toml"
    "README.md"
  )

  declare -A seen
  local -a files=()

  _print "  Collecting files..."

  for f in "${defaults[@]}"; do
    if [[ -z "${seen["$f"]+x}" ]]; then
      seen["$f"]=1
      files+=("$f")
    fi
  done

  for f in "${extra_files[@]}"; do
    if [[ -z "${seen["$f"]+x}" ]]; then
      seen["$f"]=1
      files+=("$f")
    fi
  done

  if [[ "${include_modified}" -eq 1 ]]; then
    while IFS= read -r f; do
      [[ -z "${f}" ]] && continue
      if [[ -z "${seen["$f"]+x}" ]]; then
        seen["$f"]=1
        files+=("$f")
      fi
    done < <(_git_list_modified || true)

    while IFS= read -r f; do
      [[ -z "${f}" ]] && continue
      if [[ -z "${seen["$f"]+x}" ]]; then
        seen["$f"]=1
        files+=("$f")
      fi
    done < <(_git_list_staged || true)
  fi

  if [[ "${include_untracked}" -eq 1 ]]; then
    while IFS= read -r f; do
      [[ -z "${f}" ]] && continue
      if [[ -z "${seen["$f"]+x}" ]]; then
        seen["$f"]=1
        files+=("$f")
      fi
    done < <(_git_list_untracked || true)
  fi

  local copied=0
  for rel in "${files[@]}"; do
    if [[ -e "${repo_root}/${rel}" ]]; then
      _copy_one "${repo_root}" "${bundle_dir}" "${rel}"
      copied=$((copied + 1))
    else
      _warn "Skipping (not found): ${rel}"
    fi
  done

  (
    cd "${repo_root}"
    git rev-parse HEAD > "${bundle_dir}/meta/git_head.txt" 2>/dev/null || true
    git status --porcelain=v1 > "${bundle_dir}/meta/git_status_porcelain.txt" 2>/dev/null || true
    git status > "${bundle_dir}/meta/git_status.txt" 2>/dev/null || true
    git diff > "${bundle_dir}/meta/git_diff.patch" 2>/dev/null || true
    git diff --cached > "${bundle_dir}/meta/git_diff_cached.patch" 2>/dev/null || true
    git remote -v > "${bundle_dir}/meta/git_remote.txt" 2>/dev/null || true
  )

  if _have_cmd python; then
    python --version > "${bundle_dir}/meta/python_version.txt" 2>/dev/null || true
  fi
  if _have_cmd pip; then
    pip freeze > "${bundle_dir}/meta/pip_freeze.txt" 2>/dev/null || true
  fi
  if _have_cmd uname; then
    uname -a > "${bundle_dir}/meta/uname.txt" 2>/dev/null || true
  fi

  _write_text_file "${bundle_dir}/meta/manifest.txt" \
    "bundle_name=${bundle_base}" \
    "created_utc=${ts}" \
    "repo_root=${repo_root}" \
    "copied_count=${copied}"

  if _have_cmd sha256sum; then
    (cd "${bundle_dir}" && find . -type f -print0 | xargs -0 sha256sum > "${bundle_dir}/meta/sha256sums.txt") || true
  fi

  if [[ "${make_tar}" -eq 1 ]]; then
    local tar_path="${out_dir}/${bundle_base}.tar.gz"
    (cd "${bundle_dir}" && tar -czf "${tar_path}" .)
    _print "  Tar  : ${tar_path}"
  fi

  _print "  Copied: ${copied}"
  _print "  Done  : ${bundle_dir}"
}

_main "$@"
