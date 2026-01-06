# Phase 9 Objectives And Goals

## Purpose

Phase 9 prepares PyPNM-CMTS for reliable local installation and development so Phase 10 can focus on Docker and Kubernetes readiness without reworking
fundamentals (CLI UX, configuration, packaging, and basic release/update workflows).

## Scope Summary

Phase 9 is focused on:

- Simple, repeatable installation flows (PyPI and Git).
- A minimal, operator-friendly install script (`install.sh`) that supports development and tag-based updates.
- A CMTS-focused config menu workflow aligned to `system.json` (single source of truth).
- Documentation and tests that make the above dependable and maintainable.

Phase 9 explicitly avoids implementing Docker/Kubernetes artifacts (reserved for Phase 10).

## Objectives

### O9.1 Installation Is Predictable And Documented

Provide two supported installation paths:

- PyPI install for operators.
- Git install for contributors and development environments.

Both paths must lead to a working `pypnm-cmts` CLI and a clear, minimal “first run” workflow.

### O9.2 `install.sh` Provides A Single Bootstrap Entry Point

Deliver a minimal `install.sh` that:

- Bootstraps a development environment in one command.
- Supports tag-based updates for GA and hot-fix releases.
- Runs basic verification steps and prints next actions.

### O9.3 Configuration Is CMTS-Centric And `system.json` Driven

Deliver a thin config-menu workflow that:

- Generates a valid PyPNM-CMTS `system.json`.
- Validates configuration and reports precise errors.
- Avoids re-implementing PyPNM logic; reuse where feasible and keep CMTS additions localized.

### O9.4 Release And Update Workflows Are Consistent With PyPNM

Introduce only the minimum release/update mechanics needed to:

- Install from a tag deterministically.
- Verify build artifacts locally (wheel/sdist) when requested.

Phase 9 must avoid large, speculative release automation unless it is required to meet the installation and update objectives.

### O9.5 Documentation And Tests Make The Work Durable

Add concise docs and mandatory pytest coverage for new or changed behaviors. Deprecation warnings are treated as failures (pytest/ruff).

## Goals

### G9.1 PyPI Installation

- `pip install pypnm-cmts` installs the distribution cleanly in a fresh venv.
- `pypnm-cmts --help` and `pypnm-cmts serve --help` are available immediately after install.
- A minimal config workflow is documented and produces a runnable local service (even if adapters are mocked for tests).

### G9.2 Git Installation

Support a developer-friendly path:

- `pip install -e .` for contributors (preferred).
- `pip install .` for repo snapshot installs (optional but recommended).

The docs must define the canonical commands to go from a fresh clone to `pypnm-cmts serve`.

### G9.3 `install.sh` Modes

`install.sh` supports:

- `--development`
  - Creates or uses a local venv.
  - Installs editable + dev dependencies.
  - Runs a smoke check and prints next commands.
- `--update-ga TAG`
  - Installs/updates to the specified GA tag deterministically.
  - Verifies the installed version matches the tag expectation.
- `--update-hot-fix TAG`
  - Installs/updates to the specified hot-fix tag deterministically.
  - Verifies the installed version matches the tag expectation.

Notes:

- Config migrations must be explicit and documented; do not silently mutate user configuration.
- Emojis are allowed in `install.sh` output only (per repo policy).

### G9.4 Config Menu (Thin Wrapper)

Provide a minimal CLI interface, for example:

- `pypnm-cmts config init`       Generate a baseline `system.json`.
- `pypnm-cmts config validate`   Validate configuration and report actionable errors.
- `pypnm-cmts config show`       Print effective configuration (resolved defaults + overrides).

Requirements:

- `system.json` remains the single source of truth.
- CMTS-specific namespaces are implemented as Pydantic BaseModels with one-line `Field(..., description="...")`.
- Reuse PyPNM config patterns where feasible; do not duplicate PyPNM SNMP logic in PyPNM-CMTS.

### G9.5 Tools And Scripts Consolidation (Selective)

Bring over only tooling that directly supports Phase 9:

- install/bootstrap helpers
- config generation/validation helpers
- local build verification helpers (if in scope)

Avoid bulk copying tools/scripts that are not executable or do not apply to PyPNM-CMTS.

### G9.6 Documentation

Add/refresh docs covering:

- PyPI install and first run
- Git install and development workflow
- Config initialization and validation
- Update flows using tags (GA and hot-fix)
- Common troubleshooting (missing config, venv issues, permissions)

Documentation constraints:

- Must render correctly in both MkDocs and GitHub.
- No emojis in documentation.
- Use generic placeholders where examples are needed:
  - MAC: `aa:bb:cc:dd:ee:ff`
  - IP: `192.168.0.100`

### G9.7 Tests

Mandatory pytest coverage for:

- config init output shape and defaults
- config validate error paths
- CLI argument parsing for new commands
- any update-tag resolution logic (mocked; must not require network access in tests)

## Non-Goals

The following are explicitly out of scope for Phase 9:

- Dockerfiles, Helm charts, Kubernetes manifests, or K8 APIs (Phase 10).
- Implementing new CMTS SNMP features unrelated to installation/config readiness.
- Large-scale refactors of existing orchestration/SGW behavior unless required for Phase 9 deliverables.
- Silent config migrations without explicit user/operator action.

## Acceptance Criteria

Phase 9 is complete when all of the following are true:

- Both installation paths (PyPI and Git) are documented and tested with a minimal “first run” flow.
- `install.sh --development` works on a clean environment and leaves the user with an obvious next command to run.
- Tag-based updates (`--update-ga TAG`, `--update-hot-fix TAG`) are deterministic and verified.
- Config-menu workflow can create and validate `system.json` without manual editing for a baseline dev setup.
- All new/changed behaviors have pytest coverage and tests run cleanly with no warnings.
- Repo policy constraints are satisfied (strict typing, no new Ruff ignores, SPDX 2026 headers on touched files).

## CI/CD Readiness (GitHub Actions)

Phase 9 includes a minimal CI pipeline so every change is validated across the supported interpreter range and the public-facing artifacts build cleanly.

### Objectives

- Validate runtime compatibility across **Python 3.10–3.13**.
- Build distributable artifacts (sdist + wheel) for the PyPI package **`pypnm-docsis-cmts`**.
- Validate documentation builds with **MkDocs** (fail fast on doc regressions).

### Definition Of Done

- A workflow exists under `.github/workflows/ci.yml`.
- On every push and PR:
  - `pytest` runs for Python 3.10, 3.11, 3.12, 3.13.
  - `ruff` runs (if configured for the repo).
  - `python -m build` creates `dist/*.whl` and `dist/*.tar.gz`.
  - `twine check dist/*` passes.
  - `mkdocs build --strict` passes (docs must compile without warnings).
- The package name in `pyproject.toml` is **`pypnm-docsis-cmts`**.

### Notes

- The CI workflow should be **build-only** (no publishing) until we explicitly add release automation.
- If the repo uses optional dependency groups, CI should install an appropriate group (e.g., `.[dev]`) that includes test + docs tooling.

