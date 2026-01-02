# Phase 7 Burndown Plan

## Scope

Phase 7 focuses on CMTS endpoint (EP) calls backed by Serving Group Workers (SGW). The SGW layer continuously maintains an in-memory view of serving-group topology and cable-modem membership so endpoint reads are cache-first and low-latency.

A core design constraint for Phase 7 is that **SG worker count scales with the number of service groups**. Each SGW is responsible for exactly one `sg_id` and owns that SG’s cached state.

## Operating Model

- **Cache-first reads:** Endpoints return the SGW cache by default, including `snapshot_time`, `age_seconds`, and `refresh_state`.
- **Two refresh lanes:**
  - **Heavy refresh (inventory):** DS/US channels + full cable-modem membership/topology; expensive SNMP walks; runs on a configurable interval.
  - **Light refresh (state):** registration/online state deltas for known modems; cheaper polling; runs more frequently than heavy refresh and can be decoupled.
- **Explicit on-demand refresh:** Optional endpoint actions can request refresh, but must be rate-limited and bounded (paging and caps).

## Deliverables Summary

- SGW runtime manager that spawns one worker per `sg_id`.
- Cache models for SG inventory and modem membership/state, including timestamps.
- Endpoints:
  - `/cmts/servingGroup/get/ids`
  - `/cmts/servingGroup/get/cableModems` (SG-scoped by default)
  - `/cmts/servingGroup/get/topology`
  - Optional: `/cmts/get/cableModems` (CMTS-wide, paginated, explicit)
- Container/K8 startup behavior: discovery -> SGW spawn -> readiness.
- Deterministic tests for SGW cache behavior and endpoint contracts.

## Phase 7.1 Configuration, Types, and Contracts

### Objective
Introduce configuration keys and typed contracts required for SGW polling and cache metadata.

### Tasks
- Add settings fields (and defaults) for:
  - `sgw.enabled`
  - `sgw.poll_heavy_seconds`
  - `sgw.poll_light_seconds`
  - `sgw.max_workers` (cap for safety; default derived from discovered SG count)
  - `sgw.refresh_jitter_seconds` (avoid thundering herd)
  - `sgw.cache_max_age_seconds` (for endpoint staleness indicators)
- Define cache metadata model:
  - `snapshot_time`
  - `age_seconds`
  - `last_heavy_refresh`
  - `last_light_refresh`
  - `refresh_state` (OK/STALE/ERROR)
  - `last_error` (optional message, bounded length)

### Done Criteria
- New settings validated and loadable via system config + env overrides.
- Cache metadata model is stable and used by downstream models.
- Unit tests cover defaulting and validation.

## Phase 7.2 SGW Manager Skeleton

### Objective
Create the SGW manager that owns worker lifecycle and routes cache lookups by `sg_id`.

### Tasks
- Implement `ServingGroupWorkerManager` (name flexible) that:
  - Accepts discovered `sg_ids`
  - Spawns one worker per `sg_id` (subject to `max_workers`)
  - Exposes `get_snapshot(sg_id)` and `get_all_sg_ids()`
  - Provides lifecycle controls: `start()`, `stop()`, `is_ready()`
- Add concurrency primitives:
  - Per-worker locks for snapshot replacement
  - Manager-level registry lock

### Done Criteria
- Manager starts with N workers where N == min(discovered_sg_count, max_workers).
- Manager stop is deterministic and joins worker threads/tasks.
- Unit tests validate worker count scaling behavior.

## Phase 7.3 SG Discovery at Startup

### Objective
Perform SG discovery at startup and initialize SGW workers based on discovered SG inventory.

### Tasks
- Implement startup flow:
  - Connect to CMTS
  - Discover serving groups (source: discovery service)
  - Build SG list
  - Start SGW manager with that list
- Define readiness gating:
  - “Ready” when discovery succeeded and each SGW has at least one snapshot (or a bounded timeout with partial readiness, if desired)

### Done Criteria
- Startup logs show discovered SG list and worker spawn count.
- Readiness indicates whether SGW cache is populated.
- Integration test with monkeypatched discovery returns deterministic SG list.

## Phase 7.4 SGW Polling Loop and Cache Models

### Objective
Implement SGW polling that maintains cache for DS/US/CM membership and lightweight registration state.

### Tasks
- Define SG snapshot model fields:
  - `sg_id`
  - `ds_channels` (summary)
  - `us_channels` (summary)
  - `cable_modems` (membership + minimal identity fields)
  - `topology` (optional data structure per your plan)
  - `meta` (cache metadata)
- Implement per-worker loop:
  - Heavy refresh every `poll_heavy_seconds`
  - Light refresh every `poll_light_seconds`
  - Jitter applied per SGW start
- Ensure snapshot replacement is atomic:
  - Build new snapshot -> swap under lock -> update metadata

### Done Criteria
- SGW produces snapshots on schedule.
- Failures update `refresh_state=ERROR` with bounded error text.
- Unit tests with fake pollers validate refresh scheduling order.

## Phase 7.5 Endpoint Implementation (Cache-First)

### Objective
Expose cache-backed endpoints that are fast and predictable.

### Endpoints
- `POST /cmts/servingGroup/get/ids`
  - Returns discovered SG ids and cache status summary.
- `POST /cmts/servingGroup/get/cableModems`
  - **Requires `sg_id`** (default behavior: SG-scoped).
  - Supports pagination: `page`, `page_size`.
  - Returns cache snapshot metadata.
- `POST /cmts/servingGroup/get/topology`
  - Requires `sg_id`.
  - Returns cached topology object + metadata.
- Optional: `POST /cmts/get/cableModems`
  - CMTS-wide, always paginated; aggregates from SGW caches only (no implicit SNMP walks).

### Done Criteria
- Endpoints return cache metadata (`snapshot_time`, `age_seconds`) on every response.
- CMTS-wide modem endpoint (if implemented) aggregates cached SGWs only and never triggers implicit discovery.
- Contract tests validate response shape and pagination.

## Phase 7.6 On-Demand Refresh Controls (Optional but Recommended)

### Objective
Support explicit refresh requests with safeguards.

### Tasks
- Add request options:
  - `refresh: "none" | "light" | "heavy"`
  - `max_wait_seconds` (bounded)
- Add rate limiting per SGW:
  - Do not allow multiple heavy refreshes within a minimum interval
- Ensure refresh never blocks the main loop indefinitely:
  - If refresh is in-flight, return current snapshot + `refresh_state=IN_PROGRESS`

### Done Criteria
- Endpoints can request refresh without blocking indefinitely.
- Tests verify rate limiting and bounded waits.

## Phase 7.7 Docker and Kubernetes Startup Integration

### Objective
Ensure pypnm-cmts starts correctly in containers and K8 with predictable readiness/liveness behavior.

### Tasks
- Add “startup sequence” to the service entrypoint:
  - Load config
  - Discover SGs
  - Start SGW manager
  - Expose readiness when SGW meets minimum snapshot criteria
- Provide K8 probes guidance:
  - Liveness: process health
  - Readiness: SG discovery + SGW cache readiness

### Done Criteria
- Local Docker run shows successful startup and readiness transition.
- K8-ready hooks are documented and testable.

## Phase 7.8 Observability

### Objective
Add logging and minimal metrics for SGW health.

### Tasks
- Per-SGW logs:
  - heavy refresh start/end + duration
  - light refresh start/end + duration
  - errors with bounded message
- Manager logs:
  - worker spawn count and mapping
  - stop/join results

### Done Criteria
- Logs are structured enough to diagnose a single SGW.
- No excessive per-modem logs in normal operation.

## Phase 7.9 Test Plan

### Objective
Lock in behavior with deterministic tests mirroring Phase 6.5 rigor.

### Required Tests
- Worker count scaling:
  - discovered SG count -> spawned SGW count (cap enforced)
- Cache update contract:
  - snapshot changes are visible to endpoints on subsequent calls
- Endpoint behaviors:
  - SG-scoped `/get/cableModems` requires `sg_id`
  - pagination stable and deterministic
- Refresh gating:
  - on-demand heavy refresh rate limited

### Done Criteria
- Tests pass under `pytest -q` and are deterministic (no real sleep; use injected sleepers/fake clocks).

## Phase 7.10 Documentation

### Objective
Provide concise docs aligned with existing documentation conventions.

### Tasks
- Add docs for each endpoint:
  - request/response schema
  - cache metadata semantics
  - refresh options and safeguards
- Add ops docs:
  - startup sequence
  - recommended polling intervals
  - K8 probe examples

### Done Criteria
- MkDocs/GitHub rendering is clean.
- Examples use `aa:bb:cc:dd:ee:ff` and `192.168.0.100` where applicable.

## Phase 7.11 Hardening and Follow-ons

### Objective
Optional hardening tasks that can be deferred if Phase 7 needs to ship quickly.

### Candidates
- Snapshot persistence (warm-start cache) per SGW
- Backpressure if CMTS-wide membership is huge
- Incremental SNMP walk strategies
- Cache eviction policies

## Suggested Sequencing for Codex

1. Phase 7.1 (settings + models + tests)
2. Phase 7.2 (manager skeleton + scaling tests)
3. Phase 7.3 (startup discovery -> spawn)
4. Phase 7.4 (poll loops + cache metadata)
5. Phase 7.5 (endpoints + contract tests)
6. Phase 7.7/7.8/7.10 (container/K8 + observability + docs)

