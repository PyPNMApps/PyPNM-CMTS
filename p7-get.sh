#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Build a Phase 7.5 review bundle under ./output/p7.5-bundle/ (one file per section + an index),
# and also generate a single consolidated "chat input" file to paste into ChatGPT/Codex.

set -euo pipefail
IFS=$'\n\t'

ROOT_DIR="${1:-.}"
OUT_DIR="${ROOT_DIR%/}/output/p7.5-bundle"

INDEX_PATH="${OUT_DIR}/index.txt"
CHAT_INPUT_PATH="${OUT_DIR}/p7.5-phase75-chat-input.txt"

MIN_LINES_FOR_OPTIONAL_SECTION=20

die() {
  printf 'ERROR: %s\n' "$1" 1>&2
  exit 1
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "Missing required command: $1"
}

require_cmd sed
require_cmd find
require_cmd grep
require_cmd sort
require_cmd wc
require_cmd tr
require_cmd date
require_cmd cat

mkdir -p "${OUT_DIR}"
: > "${INDEX_PATH}"

print_index_line() {
  printf '%s\n' "$1" >> "${INDEX_PATH}"
}

append_file() {
  local dest_path
  local file_path

  dest_path="$1"
  file_path="$2"

  if [ ! -f "${file_path}" ]; then
    return 0
  fi

  {
    printf '\n# FILE: %s\n' "${file_path#${ROOT_DIR%/}/}"
    sed -e 's/\r$//' "${file_path}"
    printf '\n'
  } >> "${dest_path}"
}

write_section_header() {
  local dest_path
  local title

  dest_path="$1"
  title="$2"

  {
    printf '# %s\n' "${title}"
    printf '# Root: %s\n' "${ROOT_DIR}"
  } >> "${dest_path}"
}

bundle_optional_list() {
  local out_path
  local title

  out_path="$1"
  title="$2"
  shift 2

  : > "${out_path}"
  write_section_header "${out_path}" "${title}"

  for rel in "$@"; do
    if [ -f "${ROOT_DIR%/}/${rel}" ]; then
      append_file "${out_path}" "${ROOT_DIR%/}/${rel}"
    fi
  done
}

bundle_globbed_multi() {
  local out_path
  local title
  local pat

  out_path="$1"
  title="$2"
  shift 2

  : > "${out_path}"
  write_section_header "${out_path}" "${title}"

  for pat in "$@"; do
    {
      printf '\n# FIND: %s\n' "${pat}"
    } >> "${out_path}"

    while IFS= read -r f; do
      append_file "${out_path}" "$f"
    done < <(find "${ROOT_DIR}" -type f -path "${pat}" | sort)
  done
}

bundle_find_needles() {
  local out_path
  local title
  local needle

  out_path="$1"
  title="$2"
  shift 2

  : > "${out_path}"
  write_section_header "${out_path}" "${title}"

  for needle in "$@"; do
    {
      printf '\n# GREP NEEDLE: %s\n' "${needle}"
    } >> "${out_path}"

    while IFS= read -r f; do
      if grep -q "${needle}" "$f" 2>/dev/null; then
        append_file "${out_path}" "$f"
      fi
    done < <(find "${ROOT_DIR}" -type f \( -name '*.py' -o -name '*.json' -o -name '*.md' \) -print | sort)
  done
}

section_counter=0
emit_section_path() {
  local title
  local out_file
  local out_path

  title="$1"
  out_file="$2"

  section_counter=$((section_counter + 1))
  out_path="${OUT_DIR}/$(printf '%02d' "${section_counter}")-${out_file}"

  print_index_line "$(printf '%02d' "${section_counter}")  ${title}"
  print_index_line "     ${out_path#${ROOT_DIR%/}/}"
  print_index_line ""

  printf '%s\n' "${out_path}"
}

append_chat_section() {
  local title
  local file_path

  title="$1"
  file_path="$2"

  if [ ! -f "${file_path}" ]; then
    return 0
  fi

  {
    printf '\n# ==============================================================================\n'
    printf '# SECTION: %s\n' "${title}"
    printf '# FILE: %s\n' "${file_path#${ROOT_DIR%/}/}"
    printf '# ==============================================================================\n\n'
    cat "${file_path}"
    printf '\n'
  } >> "${CHAT_INPUT_PATH}"
}

append_chat_optional_if_nonempty() {
  local title
  local file_path
  local lines

  title="$1"
  file_path="$2"

  if [ ! -f "${file_path}" ]; then
    return 0
  fi

  if [ ! -s "${file_path}" ]; then
    return 0
  fi

  lines="$(wc -l < "${file_path}" | tr -d ' ')"
  if [ "${lines}" -lt "${MIN_LINES_FOR_OPTIONAL_SECTION}" ]; then
    return 0
  fi

  append_chat_section "${title}" "${file_path}"
}

print_index_line "Phase 7.5 Review Bundle"
print_index_line "Root: ${ROOT_DIR}"
print_index_line "Output: ${OUT_DIR#${ROOT_DIR%/}/}"
print_index_line ""

# 01 Operational routes
p01="$(emit_section_path "Operational Routes (Ready/Status) Pattern" "operational_routes.txt")"
bundle_optional_list "${p01}" "Operational Routes (Ready/Status) Pattern" \
  "src/pypnm_cmts/api/routes/operational/router.py" \
  "src/pypnm_cmts/api/routes/operational/service.py" \
  "src/pypnm_cmts/api/routes/operational/schemas.py" \
  "src/pypnm_cmts/api/routes/operational/__init__.py"

# 02 SGW startup/runtime
p02="$(emit_section_path "SGW Startup + Runtime State (Discovery vs Prime Failure Semantics)" "sgw_startup_runtime.txt")"
bundle_optional_list "${p02}" "SGW Startup + Runtime State (Discovery vs Prime Failure Semantics)" \
  "src/pypnm_cmts/sgw/startup.py" \
  "src/pypnm_cmts/sgw/runtime_state.py" \
  "src/pypnm_cmts/sgw/manager.py" \
  "src/pypnm_cmts/sgw/__init__.py"

# 03 SGW snapshot/cache models
p03="$(emit_section_path "SGW Snapshot / Cache Models (Meta: snapshot_time, age_seconds, refresh_state, last_error)" "sgw_snapshot_cache_models.txt")"
bundle_globbed_multi "${p03}" "SGW Snapshot / Cache Models (Meta: snapshot_time, age_seconds, refresh_state, last_error)" \
  "*/pypnm_cmts/sgw/*model*.py" \
  "*/pypnm_cmts/sgw/*snapshot*.py" \
  "*/pypnm_cmts/sgw/*cache*.py" \
  "*/pypnm_cmts/sgw/*schemas*.py"

# 04 API composition
p04="$(emit_section_path "API Composition (How Routers Are Included)" "api_composition.txt")"
bundle_optional_list "${p04}" "API Composition (How Routers Are Included)" \
  "src/pypnm_cmts/api/app.py" \
  "src/pypnm_cmts/api/router.py" \
  "src/pypnm_cmts/api/routes/__init__.py" \
  "src/pypnm_cmts/api/__init__.py"

# 05 Existing CMTS routes
p05="$(emit_section_path "CMTS Routes (Existing Patterns Under /cmts If Any)" "existing_cmts_routes.txt")"
bundle_globbed_multi "${p05}" "CMTS Routes (Existing Patterns Under /cmts If Any)" \
  "*/pypnm_cmts/api/routes/cmts/*/*.py" \
  "*/pypnm_cmts/api/routes/cmts/*.py"

# 06 Response envelope / common models
p06="$(emit_section_path "Response Envelope / Common Models (If Present)" "response_envelope_models.txt")"
bundle_globbed_multi "${p06}" "Response Envelope / Common Models (If Present)" \
  "*/pypnm_cmts/api/*schema*.py" \
  "*/pypnm_cmts/api/*model*.py" \
  "*/pypnm_cmts/api/*response*.py"

# 07 Constants/types/settings
p07="$(emit_section_path "Core Constants / Types / Settings Used By Endpoints" "constants_types_settings.txt")"
bundle_optional_list "${p07}" "Core Constants / Types / Settings Used By Endpoints" \
  "src/pypnm_cmts/lib/constants.py" \
  "src/pypnm_cmts/lib/types.py" \
  "src/pypnm_cmts/config/orchestrator_config.py" \
  "src/pypnm_cmts/config/settings.py" \
  "src/pypnm_cmts/settings/system.json" \
  "src/pypnm_cmts/settings/system.default.json" \
  "src/pypnm_cmts/settings/system.schema.json"

# 08 SGW startup tests
p08="$(emit_section_path "Existing Tests Related To SGW Startup Semantics" "sgw_startup_tests.txt")"
bundle_optional_list "${p08}" "Existing Tests Related To SGW Startup Semantics" \
  "tests/test_sgw_startup.py"

# 09 API tests
p09="$(emit_section_path "API Tests (If Any Exist Already)" "api_tests.txt")"
bundle_globbed_multi "${p09}" "API Tests (If Any Exist Already)" \
  "tests/api/*.py" \
  "tests/test_api*.py" \
  "tests/*ops*.py"

# 10 Search matches
p10="$(emit_section_path "Search Matches (SGW Prime Failure Helper / Readiness / CMTS ServingGroup Routes)" "search_matches.txt")"
bundle_find_needles "${p10}" "Search Matches (SGW Prime Failure Helper / Readiness / CMTS ServingGroup Routes)" \
  "set_sgw_startup_prime_failure" \
  "SGW_PRIME" \
  "/cmts/servingGroup/get"

# Index summary
print_index_line "Summary"
print_index_line "Sections: ${section_counter}"
print_index_line ""

total_lines=0
while IFS= read -r f; do
  if [ -f "${f}" ]; then
    lines="$(wc -l < "${f}" | tr -d ' ')"
    total_lines=$((total_lines + lines))
  fi
done < <(find "${OUT_DIR}" -type f -name '*.txt' | sort)

print_index_line "Total lines (all section files): ${total_lines}"
print_index_line ""

# Build consolidated chat input file (requested)
: > "${CHAT_INPUT_PATH}"
{
  printf '# Phase 7.5 Chat Input\n'
  printf '# Root: %s\n' "${ROOT_DIR}"
  printf '# Generated: %s\n' "$(date -u +'%Y-%m-%dT%H:%M:%SZ')"
  printf '\n'
} >> "${CHAT_INPUT_PATH}"

append_chat_section "Operational Routes (Ready/Status) Pattern" "${p01}"
append_chat_section "SGW Startup + Runtime State (Discovery vs Prime Failure Semantics)" "${p02}"
append_chat_section "SGW Snapshot / Cache Models" "${p03}"
append_chat_section "API Composition (How Routers Are Included)" "${p04}"
append_chat_section "Core Constants / Types / Settings Used By Endpoints" "${p07}"
append_chat_optional_if_nonempty "Existing CMTS Routes (If Present)" "${p05}"

printf 'Wrote bundle to: %s\n' "${OUT_DIR}"
printf 'Index: %s\n' "${INDEX_PATH}"
printf 'Chat input: %s\n' "${CHAT_INPUT_PATH}"
