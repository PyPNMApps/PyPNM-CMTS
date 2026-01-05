# Phase 8 Burndown Plan

## Scope

Phase 8 standardizes **CMTS endpoint request/response schemas** and aligns the **CLI + container runtime configuration surface** so endpoint behavior is deterministic across:

- `pypnm-cmts …` CLI usage
- `python -m pypnm_cmts.cli …` usage
- `serve` (FastAPI) usage in Docker and Kubernetes

Phase 8 also strengthens **live CMTS testing** so integration coverage is explicit, gated, repeatable, and safe to run in CI or operator environments.

## Primary Goals

- Establish a **canonical CMTS request schema** used across all CMTS endpoints.
- Establish a **canonical CMTS response envelope** used across all CMTS endpoints.
- Implement endpoint-level rules for:
  - **Serving-group filtering**
  - **Cable-modem filtering**, including the rule that an **empty `mac_address` list means “all modems”** unless the endpoint explicitly requires an explicit list.
  - **Refresh semantics** (cache-first, optional refresh requests) where applicable.
- Add missing **CLI arguments** for CM override parameters and wire them into settings precedence.
- Publish an ops-grade **Docker/K8 runtime contract** (env/flags, probes, state_dir mounts).
- Improve **live CMTS pytest** structure and gating (unit vs integration vs live).

## Carryovers From Phase 7

The Phase 7 SGW layer and cache-first endpoints are complete. The remaining carryovers are operational and contract hardening items that Phase 8 will close:

- Container runtime contract (entrypoint/env surface) for new CM override parameters.
- Explicit K8 probe guidance (liveness vs readiness) tied to stable ops endpoints.
- `state_dir` mount and persistence guidance for Docker/K8.
- Live CMTS integration testing harness quality and documentation.

## Non-Goals

- No new CMTS vendor support beyond existing adapter contracts.
- No Kubernetes API implementations (operators/controllers).
- No database persistence.
- No new SGW topology features beyond the existing cache models.
- No breaking API response shape changes outside the explicit Phase 8 schema standardization.

## Iteration Policy

If a step requires multiple hardening passes, label them **Step X.a, Step X.b, Step X.c**, etc., while the “current step” remains Step X. Only advance to Step X+1 after Step X acceptance criteria are met.

## Operating Model Constraints

- **Cache-first reads remain the default.** Endpoints must not trigger implicit SNMP walks unless explicitly documented.
- **Configuration precedence must be explicit and consistent.** Recommended order for Phase 8:
  1) CLI flags
  2) Environment overrides
  3) `system.json`
  4) Request body overrides (only where explicitly allowed)

## Progress / Status

- Completed steps: Steps 1a, 2a, 3a, 4a, 4b, 5a, 5b, 5c, 6a, 7a
- Current step: Step 7b
- Remaining steps: Steps 7–10
- Canonical pytest command prefix: `/home/dev01/Projects/PyPNM-CMTS/.env/bin/python -m pytest`

## Step Plan

### Phase 8 · Step 1 — Canonical CMTS Request Schema (Docs + Contract)

Goal: Define the canonical request schema contract used by CMTS endpoints.

Checklist:
- [ ] Update `docs/architecture/schema/cmts-request.md` to define the canonical request shapes:
  - CMTS serving-group filter (`serving_group.id` list)
  - CM filter (`cable_modem.mac_address` list)
  - CM override parameters (SNMPv2c write community, TFTP IPv4/IPv6) as optional request fields only when explicitly supported.
- [ ] Document the rule: **empty `mac_address` list applies to all cable modems**, unless the endpoint explicitly requires a non-empty list.
- [ ] Document validation rules (types, empty list semantics, duplicates, normalization).

Contract reference: `docs/architecture/schema/cmts-request.md`

Acceptance criteria:
- Doc page defines a single canonical contract and notes endpoint-specific deviations explicitly.
- The “empty mac list means all” rule is unambiguous and testable.

Tests to run:
- None.

### Phase 8 · Step 2 — Canonical CMTS Request Models (Pydantic) + Normalization

Goal: Implement typed request models used across endpoints.

Checklist:
- [ ] Create Pydantic models for:
  - `ServingGroupFilterModel` (list of `ServiceGroupId` or empty => all)
  - `CableModemFilterModel` (list of MACs; empty => all, unless endpoint forbids)
  - `CmOverrideParametersModel` (SNMPv2c write community, TFTP IPv4/IPv6)
  - `CmtsRequestModel` (top-level wrapper under `cmts`)
- [ ] Centralize normalization:
  - MAC format normalization and de-duplication
  - empty list semantics normalized to “all” representation
- [ ] Add unit tests for validation and normalization.

Acceptance criteria:
- Request model parsing is deterministic and shared across endpoints.
- Unit tests cover empty lists, duplicates, invalid MACs, and invalid SG IDs.

Tests to run:
- `/home/dev01/Projects/PyPNM-CMTS/.env/bin/python -m pytest -q tests/test_cmts_request_models.py`

### Phase 8 · Step 3 — Endpoint Refactor to Canonical Request Schema

Goal: Update CMTS endpoints to accept the canonical schema and apply filters correctly.

Checklist:
- [ ] For each target endpoint:
  - Parse canonical request model
  - Apply serving-group filter (explicit list or all)
  - Apply cable-modem filter (explicit list or all per contract)
- [ ] Ensure endpoint-specific deviations are explicit in docs and validated in code.

Acceptance criteria:
- Endpoints accept canonical schema with correct filter semantics.
- Endpoints that require explicit MAC lists enforce it with clear errors.

Tests to run:
- `/home/dev01/Projects/PyPNM-CMTS/.env/bin/python -m pytest -q tests/test_cmts_endpoints_request_contract.py`

### Phase 8 · Step 4 — Canonical CMTS Response Envelope

Goal: Standardize response shape across CMTS endpoints.

Checklist:
- [ ] Define `CmtsResponseModel` envelope:
  - `status`
  - `message`
  - `data`
  - `request_id` (if available)
  - cache metadata (where SGW-backed)
- [ ] Apply to all targeted endpoints.
- [ ] Add contract tests verifying stable response shape.

Acceptance criteria:
- All targeted endpoints return the same response envelope.
- Cache-backed endpoints include freshness metadata consistently.

Tests to run:
- `/home/dev01/Projects/PyPNM-CMTS/.env/bin/python -m pytest -q tests/test_cmts_response_envelope.py`

### Phase 8 · Step 5 — CLI Flags and Settings Precedence (CM Override Parameters)

Goal: Add missing CLI flags and wire them into settings precedence.

Checklist:
- [ ] Add CLI args to `pypnm-cmts`:
  - `--cm-snmpv2c-write-community`
  - `--cm-tftp-ipv4`
  - `--cm-tftp-ipv6`
- [ ] Map CLI args into settings (and optionally env var equivalents).
- [ ] Document precedence and ensure `--help` remains quiet (no config warnings).

Acceptance criteria:
- CLI accepts new flags and they override system defaults deterministically.
- Help output is quiet and side-effect free.

Tests to run:
- `/home/dev01/Projects/PyPNM-CMTS/.env/bin/python -m pytest -q tests/test_cli_cm_override_args.py`

### Phase 8 · Step 6 — Endpoint Documentation Updates

Goal: Update endpoint docs to reflect canonical request/response schemas.

Checklist:
- [ ] Update each endpoint doc page to:
  - reference canonical request schema
  - list endpoint-specific deviations (if any)
  - show examples with generic MAC/IP values
- [ ] Ensure MkDocs + GitHub rendering is clean.

Acceptance criteria:
- Docs are consistent and do not conflict with implementation.
- Examples use `aa:bb:cc:dd:ee:ff` and `192.168.0.100`.

Tests to run:
- None.

### Phase 8 · Step 6a — Live CMTS Pytest Harness (System Endpoints)

Goal: Add a live CMTS pytest lane for system endpoints that is opt-in only.

Checklist:
- [x] Add live pytest option and marker, with env-gated enablement.
- [x] Add live system endpoint tests for sysDescr and serviceGroupTopology.
- [x] Document live test env vars and command.

Acceptance criteria:
- Live tests are skipped by default and require explicit enablement.
- Live tests require env-provided hostname and community.
- Live tests exercise real SNMP calls for system endpoints.

Tests to run:
- `/home/dev01/Projects/PyPNM-CMTS/.env/bin/python -m pytest -q tests/live/test_live_system_endpoints.py`

### Phase 8 · Step 7 — Live CMTS Pytest Harness (Integration + Safety)

Goal: Improve live CMTS testing so it is explicit, gated, and repeatable.

Checklist:
- [ ] Define pytest markers and gating:
  - `unit` (default)
  - `integration` (hermetic integration with fakes)
  - `live_cmts` (requires explicit env var enablement)
- [ ] Add environment-driven config injection for live tests:
  - target CMTS host, community, state_dir overrides, timeout caps
- [ ] Ensure live tests never run by default.

Acceptance criteria:
- `pytest -q` runs only unit tests by default.
- Live tests are enabled only with explicit opt-in (env var + marker selection).
- Live tests fail fast with clear diagnostics when not configured.

Tests to run:
- `/home/dev01/Projects/PyPNM-CMTS/.env/bin/python -m pytest -q`
- `/home/dev01/Projects/PyPNM-CMTS/.env/bin/python -m pytest -q -m live_cmts` (only when configured)

### Phase 8 · Step 8 — Docker Runtime Contract

Goal: Document and validate Docker runtime behavior for schema-driven endpoints.

Checklist:
- [ ] Document container entrypoint expectations:
  - how config is loaded
  - how CLI flags/env overrides are passed
  - how `state_dir` is set and mounted
- [ ] Document recommended environment variables (if provided).
- [ ] Validate startup logs and readiness transitions in container context (manual run acceptable).

Acceptance criteria:
- Docker usage is documented end-to-end with clear examples.
- Override parameters are usable without request-body changes (unless endpoint explicitly supports request overrides).

Tests to run:
- None (manual validation acceptable; keep it documented).

### Phase 8 · Step 9 — Kubernetes Runtime Contract (Probes + Mounts + Optional Manifests)

Goal: Provide K8 guidance for probes and storage and optionally a minimal manifest set.

Checklist:
- [ ] Document probe endpoints:
  - Liveness: process health only
  - Readiness: discovery + SGW cache readiness criteria
- [ ] Document `state_dir` mount strategy:
  - ephemeral (`emptyDir`) vs persistent (PVC)
- [ ] Optional: add `deploy/` manifests (deployment/service/configmap), aligned with “one container per CMTS”.

Acceptance criteria:
- K8 probe guidance is precise and maps to stable endpoints.
- `state_dir` persistence trade-offs are documented.

Tests to run:
- None.

### Phase 8 · Step 10 — Final QA + Release Readiness

Goal: Close Phase 8 with clean regression runs and documented readiness.

Checklist:
- [ ] Run full regression suite and confirm warning hygiene.
- [ ] Run legacy-key hygiene scan.
- [ ] Confirm docs updated and consistent with implementation.
- [ ] Record release readiness notes (date/time, commands, pass/fail).

Acceptance criteria:
- `pytest -q` passes cleanly.
- `tools/hygiene/legacy_key_scan.py` reports clean.
- Phase 8 burndown updated to “Phase complete” with readiness notes.

Tests to run:
- `/home/dev01/Projects/PyPNM-CMTS/.env/bin/python -m pytest -q`
- `/home/dev01/Projects/PyPNM-CMTS/.env/bin/python tools/hygiene/legacy_key_scan.py`

## Exit Criteria

- Canonical CMTS request/response schemas implemented and adopted by targeted endpoints.
- CLI and runtime configuration surface supports CM override parameters deterministically.
- Live CMTS testing is explicit, gated, and documented.
- Docker/K8 runtime contract is documented, including probes and state_dir strategy.
