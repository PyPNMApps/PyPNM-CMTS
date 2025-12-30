# Phase 6.4 Burndown Plan (6.4.1–6.4.7)

This document defines the detailed execution plan for Phase 6.4.

Phase 6.4 must explicitly support and document two long-lived runtime patterns:

- Runner: `pypnm-cmts run-forever` (the orchestrator runtime loop).
- API Service: `pypnm-cmts serve` (the FastAPI/uvicorn webservice).

It must also introduce an opt-in third pattern:

- Combined Mode: `pypnm-cmts serve` hosts the runner loop in-process (API + runner in one process).

Clarification: `run-forever` is not inherently “the webservice.” It is the long-lived orchestrator runner. `serve` is the long-lived API process. Combined mode is a convenience deployment option, not a required or default behavior.

## 6.4.1 Runtime Contract And Terminology Alignment

### Scope
Define a precise runtime contract that standardizes expectations across `run-forever`, `serve`, and the future combined mode. This is primarily a documentation and acceptance-contract task, but it may require minimal “surface” alignment (naming, help text, logging terminology) if the existing wording is inconsistent.

### Deliverables
- A single authoritative “Runtime Model” section (doc) that defines:
  - Runner vs API service responsibilities
  - Split-process vs combined-process deployment
  - Controller/Worker/Standalone semantics
  - How `election_name`, `state_dir`, and `sg_id` binding behave by mode
- A short, explicit FAQ entry: “Is run-forever the same as running as a webservice?”

### Implementation Notes
- Prefer updating existing operational docs rather than creating multiple overlapping docs.
- Use consistent terms across docs and CLI help:
  - Runner = orchestrator loop
  - API Service = FastAPI process
  - Combined Mode = API hosts runner loop (opt-in)
- Define expectations for PID records and fallback discovery at a high level (detail is in 6.4.2/6.4.5).

### Acceptance Criteria
- Documentation clearly distinguishes runner vs API service responsibilities.
- Documentation explicitly lists supported deployment patterns with minimal example commands.
- The FAQ clarifies that run-forever is not inherently the webservice.
- No behavior changes are required to consider 6.4.1 complete (unless terminology inconsistencies are discovered that materially confuse operators).

### Tests
- None required for 6.4.1 (documentation-only), unless a CLI help string is changed, in which case update any CLI snapshot tests if present.

## 6.4.2 PID Lifecycle And Ownership Normalization

### Scope
Standardize PID file creation, naming, update cadence (if any), and cleanup semantics across runtime patterns. Ensure `/ops/status` can reliably interpret PID state, with fallback scanning remaining a secondary mechanism.

### Deliverables
- A clearly defined PID ownership model:
  - Runner-owned PID files for controller/workers in split-process mode
  - Combined mode PID ownership rules (runner still owns its PID records, but creation may be triggered by serve startup)
- Defined behavior on shutdown:
  - Best-effort PID removal on graceful shutdown
  - Safe behavior when PID removal fails (no crash)
- Defined behavior when stale PID files exist:
  - `/ops/status` reports `pid_records_stale` when none of the PIDs are running

### Implementation Notes
- Keep PID file formats stable: store a single integer PID.
- Keep naming stable and documented:
  - `controller.pid`
  - `worker_<sg_id>.pid`
  - `worker_unbound.pid` (if unbound workers are supported)
- Ensure the runner is the only component that writes worker/controller PID files in split-process mode.
- In combined mode, ensure PID directory creation and PID writing occurs at runner startup, not at FastAPI request time.
- Add a shutdown hook to remove PID files for the process when appropriate (controller/worker). Use robust exception suppression to avoid masking shutdown.

### Acceptance Criteria
- PID files are created consistently when runner processes start.
- PID files are removed on graceful runner shutdown (best effort).
- `/ops/status` continues to correctly classify:
  - `pid_records_missing` when PID directory is missing or empty
  - `pid_records_stale` when PID files exist but no recorded PIDs are running
- Combined mode writes the same PID files as split-process mode (no alternate naming).

### Tests
- Unit tests for PID lifecycle:
  - Runner start writes PID file(s) in the expected location.
  - Runner shutdown removes PID file(s) (where feasible in test harness).
- `/ops/status` tests remain valid and are extended if ownership rules change.

## 6.4.3 Serve-Only Versus Runner-Only Operational Semantics

### Scope
Ensure the operational endpoints behave predictably in environments where only one of the processes is running.

### Deliverables
- Defined and documented behavior for:
  - Serve-only: API is running but no runner process is active.
  - Runner-only: runner is active but API is not running.
- Ensure `/ops/ready` remains a “local prerequisites” check, not a cluster-wide orchestration check.

### Implementation Notes
- Serve-only should not fail readiness simply because no runner exists. Readiness should reflect API’s own prerequisites (e.g., state_dir for controller/standalone behavior if serve is configured to require it).
- Runner-only implies `/ops/*` endpoints are not available; this is acceptable but must be documented.
- Clarify that `/ops/status` reports what it can observe based on PID files and fallback scanning; if serve is running and runner is absent, it should not claim workers exist.

### Acceptance Criteria
- Serve-only:
  - `/ops/health` returns 200.
  - `/ops/version` returns metadata.
  - `/ops/status` reports no running controller/workers if no PID evidence exists and fallback cannot find any.
  - `/ops/ready` reflects serve-side prerequisites only (documented).
- Runner-only:
  - Document that `/ops/*` endpoints require the API service.

### Tests
- Extend operational API tests to cover serve-only semantics explicitly (no PID files, no fallback candidates).

## 6.4.4 Combined Mode (Opt-In) Implementation Plan

### Scope
Add an opt-in mechanism so `pypnm-cmts serve` can host the runner loop in-process. This addresses deployments where a single container/process is preferred.

### Deliverables
- A new CLI option for `serve` (final name determined during implementation) that enables combined mode, for example:
  - `pypnm-cmts serve --with-runner`
  - `pypnm-cmts serve --run-forever`
- Combined mode lifecycle:
  - runner starts when API starts
  - runner shuts down when API shuts down
- Operational behavior remains consistent:
  - PID files written as in split-process mode
  - `/ops/status` reflects the in-process runner

### Implementation Notes
- Use FastAPI lifespan events (startup/shutdown) to control runner lifecycle in combined mode.
- Runner execution model:
  - If runner is async: run as an `asyncio.Task` owned by lifespan.
  - If runner is sync/blocking: run in a dedicated thread via AnyIO/asyncio facilities with a stop signal.
- Provide a structured stop mechanism:
  - runner loop checks a stop flag/event between ticks
  - shutdown sets stop flag and waits for a bounded grace period
- Avoid introducing a process supervisor. This is not intended to respawn crashed runner loops.
- Ensure combined mode does not alter default behavior. The flag must be opt-in.

### Acceptance Criteria
- `serve` without the flag behaves exactly as today.
- `serve` with the flag starts the runner loop automatically.
- On termination, the runner loop stops gracefully and PID files are cleaned up (best effort).
- `/ops/status` reflects runner processes correctly in combined mode, without requiring fallback scanning.

### Tests
- New smoke test path:
  - Start `serve` with combined flag and verify `/ops/version` and `/ops/status` show expected visibility.
- Unit tests for lifespan runner start/stop behavior (as feasible without brittle timing).

## 6.4.5 Fallback Discovery Coverage For Both Patterns

### Scope
Ensure fallback discovery remains accurate and useful for both split-process and combined mode. It must not become overly permissive or “guessy.”

### Deliverables
- A unified fallback discovery policy:
  - strict match on `--election-name`
  - identify controller vs worker processes by args (mode)
  - optionally detect combined mode where a single process contains both API and runner indicators (if applicable)
- Document when fallback is used and its limitations.

### Implementation Notes
- Keep fallback discovery limited to:
  - `ps -eo pid,args`
  - exact `--election-name` match
  - presence of `pypnm-cmts` and a runner signature (e.g., `run-forever`)
- For combined mode, decide on a signature:
  - either the runner args remain visible in the single process command line
  - or document that fallback is not expected to infer combined mode if args are not present
- Do not broaden matching rules to substrings or partial election matches.

### Acceptance Criteria
- When PID files are missing or stale, fallback is attempted only if `election_name` is configured and non-empty.
- Fallback never reports processes from a different election name.
- Fallback remains a secondary signal: if PID files show running processes, no fallback is required.

### Tests
- Unit tests for `_extract_arg_value` remain.
- Add fallback tests that cover:
  - strict election mismatch rejection
  - worker sg-id parsing in both `--sg-id <n>` and `--sg-id=<n>` forms
  - combined-mode signature handling (depending on chosen signature approach)

## 6.4.6 Test Matrix And CI/System-Test Integration

### Scope
Expand the automated test matrix to cover split-process and combined mode as distinct supported deployments, without introducing flaky timing.

### Deliverables
- A test matrix (documented) and implemented coverage:
  - Serve-only smoke test (already present; keep stable)
  - Runner-only behavior documented (no API endpoints; may be covered by runner unit tests)
  - Combined-mode smoke test (new)
- System test script coverage:
  - Extend `tools/system-test/ops-smoke.sh` to optionally validate `/ops/status` fields beyond `"status":"ok"` (bounded scope to avoid brittle parsing).

### Implementation Notes
- Avoid tests that depend on long-running loops without stop conditions.
- Prefer:
  - bounded timeouts
  - deterministic readiness checks
  - explicit shutdown/cleanup
- Ensure smoke tests use `sys.executable` (already corrected) and run under venv.

### Acceptance Criteria
- `pytest` passes locally in venv with the expanded matrix.
- Smoke tests are stable and do not rely on external tooling beyond POSIX shell utilities.
- CI (if configured) exercises at least serve-only and combined-mode smoke tests.

### Tests
- `tests/test_ops_service_smoke.py` expanded for combined mode.
- Possibly add `tests/test_runner_lifecycle.py` (name TBD) for runner stop semantics.

## 6.4.7 Operator Documentation And Examples

### Scope
Update operator-facing documentation to explain the supported deployment patterns, recommended defaults, and how `/ops/*` endpoints should be interpreted under each pattern.

### Deliverables
- Update operational docs to include:
  - Split-process deployment instructions
  - Combined-mode deployment instructions (opt-in)
  - Serve-only semantics and limitations
  - How PID files and fallback discovery affect `/ops/status`
- Add a small “Troubleshooting” section:
  - interpreting `pid_records_missing` vs `pid_records_stale`
  - when `fallback_used` should be expected
  - common misconfigurations (missing `state_dir`, missing `sg_id` in worker mode)

### Implementation Notes
- Keep docs concise and action-oriented.
- Prefer small example blocks:
  - split-process: two commands
  - combined-mode: one command
- Ensure examples show real flag names once implemented; until then, mark combined flag as “planned” in the plan and update when implemented.

### Acceptance Criteria
- Operators can answer:
  - what to run in a container for each pattern
  - what `/ops/status` means under each pattern
  - why `run-forever` is not the same as “running the webservice”
- Documentation is consistent with implementation after 6.4.2–6.4.6 land.

## Next Implementation Focus

After this plan is committed, the next implementation prompts should focus on:

1) 6.4.2 PID lifecycle and ownership normalization
2) 6.4.4 Combined mode implementation (opt-in serve hosts runner)
