# PyPNM-CMTS Architecture And Implementation Status

This Document Defines The Software-Centric Architecture, Execution Modes, And A Deterministic Implementation Checklist For PyPNM-CMTS.

The Goal Is To Support A Standalone-First Deployment Model That Can Later Migrate Cleanly To Kubernetes Without Redesign.

## Architecture Overview

PyPNM-CMTS Is Designed To Service One CMTS Instance And Dynamically Discover Service Groups (SGs) And Cable Modems (CMs) Using SNMP.

The System Is Divided Into Four Logical Layers:

1. Discovery & Control Plane
2. Scheduling & Execution
3. Persistence & Indexing
4. API & Observability

All Layers Are Implemented In Python And Rely On Filesystem-Based Persistence. No Database Is Used.

## Execution Modes

### Standalone Mode

- One process
- Controller + SG workers + API
- In-process concurrency
- File-based coordination
- SG workers scale with Service Groups; worker pool size should be configurable (min(num_sgs, cap))

### Controller Mode

- Discovery + reconciliation only
- No workers
- Intended for Kubernetes controller pods

### Worker Mode

- One SG per process
- Intended for Kubernetes worker pods
- Polls inventory directly until message bus is introduced

## Core Principle: Serving Group Workers And Cache-First Endpoints

Phase 7 Introduces Serving Group Workers (SGWs) That Continuously Maintain An In-Memory Cache Of Serving-Group Topology And Cable-Modem Membership.

A Core Design Constraint Is That SG Worker Count Scales With The Number Of Service Groups. Each SGW Is Responsible For Exactly One sg_id And Owns That SG’s Cached State.

Endpoints Are Cache-First And Must Not Trigger Implicit Live SNMP Walks. Any Live Refresh Must Be Explicit, Rate-Limited, And Bounded.

## SGW Discovery Defaults

The default SGW discovery mode is `snmp`. Startup performs a ping + SNMP sysDescr precheck, then enumerates SG IDs via SNMP. Static discovery is supported for fixed SG lists.

## Persistence Model

Each transaction is written to disk:

```
<data_root_dir>/<cmts_id>/<sg_id>/<mac>/<YYYY>/<MM>/<DD>/<transaction_id>/
  transaction.json
  results.json
```

An append-only JSONL index is maintained per SG/day:

```
<data_root_dir>/<cmts_id>/<sg_id>/index/<YYYY-MM-DD>.jsonl
```

## Phase 7 Operating Model

- Cache-first reads: endpoints return SGW cache by default, including snapshot_time_epoch, age_seconds, and refresh_state.
- Two refresh lanes:
  - Heavy refresh (inventory): DS/US channels + full cable-modem membership/topology; expensive SNMP walks; runs on a configurable interval.
  - Light refresh (state): registration/online state deltas for known modems; cheaper polling; runs more frequently than heavy refresh and can be decoupled.
- Explicit on-demand refresh: optional endpoint actions can request refresh, but must be rate-limited and bounded (paging and caps).

## Implementation Checklist / Status

Status Markers:
- [x] Done (Implemented And Covered By Tests)
- [ ] Not Started
- [~] In Progress (Implemented But Missing Tests Or Integration)

### Phase 0 — Contracts & Wiring

- [x] CmtsOrchestratorSettings model implemented
- [x] CLI mode selection added
- [x] Adapter interface defined
- [x] Launcher interface defined
- [x] Coordination interfaces defined
- [x] Docs updated (system + CLI)

### Phase 1 — Storage & Index

- [x] Storage layout builder
- [x] Transaction writer
- [x] JSONL index append
- [x] JSONL query helpers
- [x] Pytest coverage
- [x] Docs updated (storage)

### Phase 2 — Coordination

- [x] File-based leader election
- [x] File-based SG lease with TTL
- [ ] Redis placeholder
- [ ] K8 lease placeholder
- [x] CoordinationManager (tick-loop / heartbeat + SG partitioning across replicas)
- [x] Pytest coverage (CoordinationManager)
- [x] MkDocs Mermaid support
- [ ] Docs updated (coordination)

### Phase 3 — Orchestrator Skeleton

- [ ] Discovery controller
- [ ] Reconciler
- [ ] In-process launcher
- [ ] SG worker lifecycle
- [ ] Global executor
- [ ] Standalone boot path
- [ ] Docs updated (topology)

### Phase 4 — Scheduling & Pipelines

- [ ] Modem eligibility filtering
- [ ] Cooldown enforcement
- [ ] Per-SG concurrency
- [ ] Global concurrency
- [ ] Placeholder pipeline execution
- [ ] Results written + indexed
- [ ] Pytest coverage
- [ ] Docs updated

### Phase 5 — API Exposure

- [ ] /cmts/status
- [ ] /sg/status
- [ ] /results/query
- [ ] /results/getTransaction
- [ ] API schemas documented

### Phase 6 — Kubernetes Readiness Validation

- [ ] Controller-only mode runs
- [ ] Worker-only mode runs
- [ ] No in-process assumptions in core logic
- [ ] K8 backends isolated
- [ ] Docs updated (deployment modes)

### Phase 7 — Serving Group Worker Endpoint Layer

Phase 7 Focuses On CMTS Endpoint Calls Backed By SGWs. The SGW Layer Continuously Maintains An In-Memory View Of Serving-Group Topology And Cable-Modem Membership So Endpoint Reads Are Cache-First And Low-Latency.

#### Phase 7.1 Configuration, Types, And Contracts

- [x] Add sgw.* settings fields (enabled, poll_heavy_seconds, poll_light_seconds, max_workers, refresh_jitter_seconds, cache_max_age_seconds)
- [x] Define cache metadata model (snapshot_time_epoch, age_seconds, last_heavy_refresh_epoch, last_light_refresh_epoch, refresh_state, last_error)
- [x] Unit tests cover defaulting and validation for SGW settings and metadata model

Notes:
- Cache metadata is modeled under orchestrator models and reused by SGW cache entry models.
- last_error is bounded and validation-tested.

#### Phase 7.2 SGW Manager Skeleton

- [x] Implement SGW cache store with upsert and metadata update helpers
- [x] Implement SGW manager refresh cycle skeleton (heavy/light lanes + jitter + staleness)
- [x] Deterministic unit tests for:
  - heavy refresh updates heavy + light timestamps
  - light refresh only behavior
  - jitter delaying refresh and driving refresh_state=STALE
  - error bounding behavior

Notes:
- Worker-per-sg_id lifecycle management (spawn/stop/join) is tracked under Phase 7.3 to align with startup discovery and readiness gating.

#### Phase 7.3 SG Discovery At Startup

Objective:
Perform SG discovery at startup, prime the SGW cache, and gate /ops/ready on discovery + cache priming.

Tasks:
- [x] Implement startup flow on FastAPI serve startup:
  - Load CmtsOrchestratorSettings.from_system_config()
  - Discover serving groups via CmtsInventoryDiscoveryService.run_discovery(...)
  - Start an SGW cache store + SGW manager bound to the discovered sg_id list
  - Prime the SGW cache with a single refresh_once(now_epoch) to ensure at least one snapshot per SG
- [x] Publish SGW startup status for operational endpoints:
  - startup_completed / discovery_ok / discovered_sg_ids / last_refresh_epoch / bounded error_message
  - Accessors for store + manager for endpoint and readiness checks
- [x] Gate /ops/ready on SGW discovery + cache priming:
  - Fail with SGW_DISCOVERY when startup completed and discovery_ok is false
  - Fail with SGW_CACHE when discovery_ok is true but one or more SGs lack a primed cache snapshot
  - Return explicit readiness fields: discovery_ok, discovered_sg_ids, sgw_ready, missing_sg_ids
- [x] Add deterministic tests:
  - Success path: discovery returns stable SG list and cache is primed
  - Failure path: discovery raises and /ops/ready returns 503 with SGW_DISCOVERY
  - No real sleeps (inject _now_epoch and monkeypatch discovery)

Done Criteria:
- Serve startup logs show the discovered SG list and SGW initialization summary.
- /ops/ready reflects SGW readiness with explicit discovery/cache fields.
- Tests pass under pytest -q.

#### Phase 7.4 SGW Polling Loop And Cache Models

- [ ] Define SG snapshot model fields (sg_id, ds_channels summary, us_channels summary, cable_modems membership, topology, metadata)
- [ ] Implement per-worker loop:
  - Heavy refresh every poll_heavy_seconds
  - Light refresh every poll_light_seconds
  - Jitter applied per SGW start
- [ ] Ensure snapshot replacement is atomic:
  - Build new snapshot -> swap under lock -> update metadata
- [ ] Unit tests with fake pollers validate scheduling order and error paths

#### Phase 7.5 Endpoint Implementation (Cache-First)

- [ ] POST /cmts/servingGroup/operations/get/ids
- [ ] POST /cmts/servingGroup/operations/get/cableModems (sg_id required, paginated)
- [ ] POST /cmts/servingGroup/operations/get/topology (sg_id required)
- [ ] Optional: POST /cmts/get/cableModems (CMTS-wide, always paginated, aggregates caches only)
- [ ] Contract tests validate response shape, cache metadata presence, and pagination determinism

#### Phase 7.6 On-Demand Refresh Controls

- [ ] Add request options: refresh (none|light|heavy), max_wait_seconds (bounded)
- [ ] Add per-SGW rate limiting for heavy refresh
- [ ] Ensure refresh never blocks the main loop indefinitely (in-flight returns current snapshot with explicit state token)
- [ ] Tests verify rate limiting and bounded waits

#### Phase 7.7 Container And Kubernetes Startup Integration

- [ ] Define startup sequence: load config -> discover SGs -> start SGW manager -> expose readiness
- [ ] Document probe guidance:
  - Liveness: process health
  - Readiness: SG discovery + SGW cache readiness
- [ ] Local Docker run path validated (documented and testable)

#### Phase 7.8 Observability

- [ ] Per-SGW logs:
  - heavy refresh start/end + duration
  - light refresh start/end + duration
  - errors with bounded message
- [ ] Manager logs:
  - worker spawn count and mapping
  - stop/join results
- [ ] No excessive per-modem logs in normal operation

#### Phase 7.9 Test Plan

- [ ] Worker count scaling: discovered SG count -> spawned SGW count (cap enforced)
- [ ] Cache update contract: snapshot changes visible to endpoints on subsequent calls
- [ ] Endpoint behaviors:
  - SG-scoped /get/cableModems requires sg_id
  - pagination stable and deterministic
- [ ] Refresh gating: on-demand heavy refresh rate limited
- [ ] All tests deterministic (no real sleep; injected sleepers/fake clocks)

#### Phase 7.10 Documentation

- [ ] Endpoint docs:
  - request/response schema
  - cache metadata semantics
  - refresh options and safeguards
- [ ] Ops docs:
  - startup sequence
  - recommended polling intervals
  - probe examples

#### Phase 7.11 Hardening And Follow-Ons

- [ ] Snapshot persistence (warm-start cache) per SGW
- [ ] Backpressure for CMTS-wide membership sizes
- [ ] Incremental SNMP walk strategies
- [ ] Cache eviction policies

## Final Acceptance Checklist

- [ ] Ruff passes
- [ ] Relevant pytest tests executed
- [ ] mkdocs build --strict passes (or documented exception)
- [ ] No database introduced
- [ ] PyPNM core not modified unintentionally
- [ ] Changes aligned with AGENTS.md
