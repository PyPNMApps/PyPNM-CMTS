# PyPNM-CMTS TODO

Last Updated: 2026-01-04 (America/Denver)

This is the running, repo-wide TODO list for **PyPNM-CMTS**. Items are written so they can be checked off by Codex as work completes.

## Phase 7.7 Closeout Items

- [x] Make `SgwCacheStore` thread-safe (lock + copy-on-read/copy-on-write).
- [x] Add unit coverage for store copy isolation + concurrency smoke.
- [x] Ensure thread-safety test fails on hangs; make exception capture thread-safe.
- [x] Normalize legacy `retrival_method` to canonical `retrieval_method` and remove noisy warnings for empty/missing `tftp.remote_dir`.
- [x] Install `pytest-asyncio` in test extras and set `asyncio_mode` to remove `PytestConfigWarning`.
- [x] Perform legacy-key hygiene scan; keep only explicit backwards-compatibility notes/fallback code.

## Architecture And Operating Model

- [ ] Document the end-to-end CMTS container operating model (one container per CMTS, config layout, ports, file transfer endpoints).
- [ ] Document Service Group Worker scaling rule (1 SGW per `sg_id`) and how worker count is derived/configured.
- [ ] Define and document the cache contract (snapshot fields, refresh lanes, staleness semantics, error semantics).
- [ ] Add a lightweight “Performance and Sizing” note (expected SG count, modem count, polling intervals, CPU/RAM guidance).

## SGW Manager And Refresh Loop

- [ ] Add deterministic jitter strategy option (e.g., stable hash of `sg_id`) and document tradeoffs vs random.
- [ ] Add guardrails for misconfiguration (e.g., `poll_light_seconds` > `poll_heavy_seconds`, negative intervals).
- [ ] Add unit tests for:
  - [ ] Heavy due vs light due precedence with jitter and request overrides.
  - [ ] Heavy refresh rate-limit acceptance/rejection edge cases.
  - [ ] Service-group set changes while refresh loop is running (concurrency boundary conditions).
- [ ] Add explicit “refresh request queue depth” metric per SG (or a counter) to improve observability of user-driven refreshes.

## SGW Cache Store And Data Model

- [ ] Add `delete_entry(sg_id)` and `clear()` APIs if needed for lifecycle operations and tests.
- [ ] Add a store-level “contract” docstring describing copy semantics (return values are safe to mutate).
- [ ] Evaluate cost of deep-copy for large snapshots; document expected scale and mitigation options.

## Startup, Readiness, And Lifecycle

- [ ] Ensure startup prime is bounded (timeout) and surfaces actionable readiness errors.
- [ ] Add a startup health report model that includes discovery status, prime status, and timestamp.
- [ ] Add graceful shutdown integration (stop SGW background refresh on app shutdown hook).

## CMTS Discovery And Inventory

- [ ] Implement vendor-neutral SG discovery interface (SNMP-backed) and a test double for hermetic tests.
- [ ] Add topology and membership “heavy refresh” inventory provider (DS/US channels, modem membership).
- [ ] Add “light refresh” state provider (registration/online deltas) for known modems.
- [ ] Add capability flags per CMTS vendor/OS (what OIDs and features are supported).

## FastAPI Endpoints

- [ ] Validate endpoint schema coverage against the cache contract:
  - [ ] `/cmts/servingGroup/get/ids`
  - [ ] `/cmts/servingGroup/get/cableModems`
  - [ ] `/cmts/servingGroup/get/topology`
  - [ ] `/cmts/servingGroup/status`
  - [ ] `/ops/ready`
- [ ] Add endpoint-level pagination and sorting consistency tests (stable ordering, page boundary correctness).
- [ ] Add “refresh” endpoint documentation (rate limits, wait semantics, staleness behavior).
- [ ] Add response examples to docs for each endpoint (cache cold, cache warm, stale, error).

## CLI And Operator UX

- [ ] Ensure `install.sh` and `scripts/setup-and-test.sh` support:
  - [ ] Custom venv path
  - [ ] Offline/airgapped mode (optional)
  - [ ] Deterministic tool versions (pinning guidance)
- [ ] Add a `pypnm-cmts doctor` command (or equivalent) to validate:
  - [ ] Config file presence/shape
  - [ ] Connectivity prerequisites
  - [ ] SNMP credentials
  - [ ] File transfer dependencies (if applicable)

## Configuration And Secrets

- [ ] Standardize configuration key naming and document backward-compatibility policy (what is supported and for how long).
- [ ] Add a config schema validation command (CLI) with clear errors and exit codes.
- [ ] Add explicit guidance for secrets handling (env vars, files, encryption policy, permissions).

## Testing Strategy

- [ ] Add high-signal hermetic tests for:
  - [ ] SG discovery service contract (happy path + failure modes)
  - [ ] Heavy poller and light poller integration with manager/store
  - [ ] Startup service in enabled/disabled modes (already partial)
- [ ] Add minimal integration test harness for “simulated CMTS” behavior (fake SNMP agent or stub service).
- [ ] Add CI test matrix (Python 3.10–3.13) and enforce `-W error` selectively where safe.

## Logging, Metrics, And Observability

- [ ] Add structured logging fields for `owner_id`, `run_id`, `sg_id`, `refresh_mode`, and error codes.
- [ ] Add metrics surface (even if initially log-based):
  - [ ] refresh durations (heavy/light)
  - [ ] per-SG staleness age
  - [ ] error counters by type
  - [ ] request-refresh counters and rate-limit counters

## Performance And Resilience

- [ ] Add backoff strategy for repeated SG failures (avoid hot-looping on broken SG).
- [ ] Add circuit-breaker style state for “SG unhealthy” with cooldown.
- [ ] Add batch SNMP strategy notes (walk vs get-bulk), including timeout/retry tuning guidance.

## Packaging, Versioning, And Release Hygiene

- [ ] Confirm consistent version bump flow across PyPNM and PyPNM-CMTS (tagging, changelog, release notes).
- [ ] Add a minimal CHANGELOG.md policy and release checklist.
- [ ] Validate wheels/sdist build in CI, and add smoke install test.

## Documentation

- [ ] Ensure MkDocs structure includes:
  - [ ] Architecture overview (controller + SGW)
  - [ ] Endpoint contract pages
  - [ ] Configuration reference
  - [ ] Deployment examples (local, container, Kubernetes sketches)
- [ ] Add diagrams for:
  - [ ] SGW cache-first reads
  - [ ] Heavy vs light refresh lanes
  - [ ] One container per CMTS deployment topology
- [ ] Keep `AGENTS.md` aligned with user-specified response preferences (record updates here).
- [ ] Use the agent review bundle as the primary communication artifact for changes (reference it in responses).

## Security And QA

- [ ] Run repository-wide hygiene scans periodically (MAC/IP allowlist, secrets scanners).
- [ ] Add `ruff` and `pyright` checks to CI (with a staged rollout plan).
- [ ] Add `pip-audit` (or equivalent) to CI and document vulnerability response process.
