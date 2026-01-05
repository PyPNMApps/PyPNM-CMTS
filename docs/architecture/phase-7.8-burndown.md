# Phase 7.8 Burndown

## Scope

Phase 7.8 focuses on hardening SG worker discovery, refresh lanes, and cache-first endpoint behavior while improving operational resilience and observability. The SG worker scaling model remains one SGW per `sg_id`, and cache-first reads remain the default contract for all endpoints.

## Non-Goals

- No Kubernetes API implementations.
- No database persistence.
- No new CMTS vendor support beyond the existing adapter contracts.
- No API response shape changes unless explicitly approved in later steps.

## Progress / Status

- Completed steps: Step 8, Step 9, Step 10
- Current step: Phase complete
- Remaining steps: none
- Canonical pytest command prefix: `/home/dev01/Projects/PyPNM-CMTS/.env/bin/python -m pytest`

## Operating Model

### Cache-First Reads

Endpoints return SGW cache snapshots by default, including freshness metadata. Live polling remains opt-in and rate-limited.

### Heavy vs Light Refresh Lanes

Heavy refresh updates inventory and topology (DS/US + membership). Light refresh updates registration/state deltas for already-known modems.

### SG Worker Scaling

One SGW per `sg_id`. Worker count scales with discovered SG count and remains bounded by configuration caps.

## Step Plan

### Phase 7.8 · Step 1

Goal: Reset burndown and TODO planning for Phase 7.8.

Checklist:
- [ ] Create Phase 7.8 burndown document.
- [ ] Reset TODO list to Phase 7.8 step numbering.
- [ ] Archive Phase 7.7 documentation references.

Acceptance criteria:
- Burndown and TODO are Phase 7.8 labeled.
- Phase 7.7 artifacts are discoverable via archive references.

Tests to run:
- None.

### Phase 7.8 · Step 2

Goal: Define the SG discovery contract and a static discovery implementation.

Checklist:
- [ ] Document SG discovery interface and expected outputs.
- [ ] Add a static discovery provider with deterministic test data.

Acceptance criteria:
- Discovery contract documented and consumed by SGW startup.
- Static provider used in hermetic tests.

Tests to run:
- `/home/dev01/Projects/PyPNM-CMTS/.env/bin/python -m pytest -q tests/test_sgw_startup.py`

### Phase 7.8 · Step 3

Goal: Implement real SNMP-based SG discovery via PyPNM integration.

Checklist:
- [ ] Add an SNMP discovery provider behind the discovery interface.
- [ ] Add a discovery mode selector (static vs snmp) with safe defaults.
- [ ] Add hermetic SNMP discovery contract tests.

Acceptance criteria:
- SNMP discovery returns sorted, deduped `ServiceGroupId` values.
- Discovery mode selection defaults to static but supports SNMP when enabled.
- Failure modes are explicit and surfaced to startup.

Tests to run:
- `/home/dev01/Projects/PyPNM-CMTS/.env/bin/python -m pytest -q tests/test_sgw_discovery_snmp_contract.py`
- `/home/dev01/Projects/PyPNM-CMTS/.env/bin/python -m pytest -q tests/test_sgw_startup.py`

### Phase 7.8 · Step 4

Goal: Harden heavy refresh inventory pipeline.

Checklist:
- [ ] Validate DS/US channel collection in heavy refresh.
- [ ] Ensure membership snapshots are consistent and ordered.

Acceptance criteria:
- Heavy refresh populates cache with correct channel and modem data.
- Cache metadata reflects heavy refresh timestamps.

Tests to run:
- `/home/dev01/Projects/PyPNM-CMTS/.env/bin/python -m pytest -q tests/test_sgw_manager_refresh.py::test_sgw_manager_heavy_refresh_replaces_snapshot_payload`
- `/home/dev01/Projects/PyPNM-CMTS/.env/bin/python -m pytest -q tests/test_sgw_heavy_refresh_inventory.py`

### Phase 7.8 · Step 5

Goal: Harden light refresh delta pipeline.

Checklist:
- [ ] Define light refresh state model expectations.
- [ ] Ensure light refresh respects membership list boundaries.

Acceptance criteria:
- Light refresh updates only state fields and preserves membership list.
- Rate limits and cache age updates behave deterministically.

Tests to run:
- `/home/dev01/Projects/PyPNM-CMTS/.env/bin/python -m pytest -q tests/test_sgw_manager_refresh_extra.py::test_sgw_manager_light_refresh_updates_modems`

### Phase 7.8 · Step 6

Goal: Harden SGW lifecycle start/stop behavior.

Checklist:
- [ ] Validate startup prime and background refresh shutdown hooks.
- [ ] Confirm stop signals cleanly terminate refresh threads.

Acceptance criteria:
- Background refresh stops cleanly and does not hang on shutdown.
- Startup readiness accurately reflects cache priming.

Tests to run:
- `/home/dev01/Projects/PyPNM-CMTS/.env/bin/python -m pytest -q tests/test_sgw_background_refresh.py`

### Phase 7.8 · Step 7

Goal: Validate endpoint refresh semantics and rate limiting.

Checklist:
- [ ] Confirm refresh request modes map to manager requests.
- [ ] Validate max-wait and require-fresh behavior under load.

Acceptance criteria:
- Refresh requests respect rate limits and wait semantics.
- Endpoints return consistent metadata for refresh outcomes.

Tests to run:
- `/home/dev01/Projects/PyPNM-CMTS/.env/bin/python -m pytest -q tests/test_sgw_endpoints.py`

### Phase 7.8 · Step 8

Goal: Observability pass (structured logs and metrics stubs).

Checklist:
- [x] Add structured fields to SGW logs.
- [x] Add metrics stubs for refresh durations and staleness.

Acceptance criteria:
- Logs include `sg_id`, `refresh_mode`, and timing fields.
- Metrics stubs are documented and unit-tested.

Tests to run:
- `/home/dev01/Projects/PyPNM-CMTS/.env/bin/python -m pytest -q tests/test_sgw_readiness.py`
- `/home/dev01/Projects/PyPNM-CMTS/.env/bin/python -m pytest -q tests/test_sgw_observability.py`

### Phase 7.8 · Step 9

Goal: Load-safety and contention review.

Checklist:
- [x] Review store copy boundaries under load.
- [x] Validate lock usage in high-frequency reads/writes.

Acceptance criteria:
- Store remains safe under concurrent access.
- No aliasing regressions reintroduced.

Tests to run:
- `/home/dev01/Projects/PyPNM-CMTS/.env/bin/python -m pytest -q tests/test_sgw_store_thread_safety.py`

### Phase 7.8 · Step 10

Goal: Final QA and release readiness.

Checklist:
- [x] Run targeted regression suite.
- [x] Perform legacy-key hygiene scan.
- [x] Update release readiness notes.

Acceptance criteria:
- Regression suite passes cleanly.
- Legacy-key hygiene scan completed and documented.

Tests to run:
- `/home/dev01/Projects/PyPNM-CMTS/.env/bin/python -m pytest -q`

## Exit Criteria

- All Phase 7.8 steps completed with acceptance criteria met.
- Cache-first endpoint behavior and SGW scaling model validated.
- Regression tests pass with no new warnings.

## Release Readiness Notes

- Date/time: 2026-01-04 19:46:57 MST
- Regression suite: `/home/dev01/Projects/PyPNM-CMTS/.env/bin/python -m pytest -q` (passed)
- Warning hygiene: no pytest warnings; expected skips only
- Legacy-key hygiene scan: `/home/dev01/Projects/PyPNM-CMTS/.env/bin/python tools/hygiene/legacy_key_scan.py` (clean)
