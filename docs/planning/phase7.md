# Phase 7 – Serving Group Worker Endpoint Plan

Phase 7 Concentrates On CMTS Endpoint Calls Backed By Serving Group Workers (SGWs). SGWs Maintain A Cached View Of CMTS Inventory And State So Endpoints Are Fast, Predictable, And Scalable In Docker And Kubernetes Deployments.

## Objectives

- Implement `pypnm-cmts` startup for the Webservice (Docker + Kubernetes).
- At startup, connect to the CMTS and discover Serving Groups (SGs).
- Create and run SG Workers (SGWs) based on the discovered SG inventory.
- SGWs periodically maintain a cached view of:
  - Downstream (DS) channels
  - Upstream (US) channels
  - Cable modems (CMs)
- SGW data is kept in memory so endpoints can respond quickly without triggering a live poll for each request.

## Architectural Fit With The Existing Orchestrator

Phase 6.5 introduced stable controller/combined/worker coordination and leadership transitions. Phase 7 should reuse that machinery rather than invent a second scheduler.

Recommended mapping:

- Controller/leader responsibilities:
  - Discovery and publishing of the global SG inventory
  - Shard planning (SG → SGW assignment) using existing planning logic
- Worker responsibilities (including combined mode):
  - Hold leases for assigned SGs
  - Run one SGW per leased SG (or per shard) and keep that SG’s cache fresh
- Endpoint responsibilities:
  - Serve cache-backed results for SG-scoped requests
  - Provide CMTS-wide endpoints only when explicitly requested, always paginated

This keeps SGW ownership aligned with leases and makes scale-out in Kubernetes straightforward.

## Core Principle: Cache-First Endpoints

“All cable modems on the CMTS” can be expensive if executed as an on-demand SNMP walk (device load, latency, payload size). Phase 7 defaults to cache-backed reads:

- SGWs poll on a configurable interval (e.g., 5/10/15 minutes) and refresh inventory caches.
- Endpoints return cached results by default.
- “Live” refresh is possible but must be explicit, privileged, and rate-limited.

Even when cache-backed, returning the full CMTS modem list can be expensive for memory, serialization, and network egress. Address this by:
- Scoping by SG wherever possible
- Pagination for CMTS-wide requests
- Summary modes for large views (counts + timestamps rather than full modem objects)

## Inventory Refresh Versus State Refresh

Separate the cadence for “heavy inventory” from “light state.” This directly addresses your point that “all cable modems on the CMTS” is only expensive when it triggers polling; cache hits should be cheap, but registration state can still drift between polls.

### Heavy Inventory Refresh (Slower)
- Interval: 5–15 minutes (configurable)
- Data: modem membership per SG, DS/US inventory, topology inputs, per-SG modem identity data

### Light State Refresh (Faster)
- Interval: 30–60 seconds (configurable) or on-demand using a freshness gate
- Data: minimal “is registered / online” state plus a small set of health flags
- Goal: answer “is the CM still registered?” without re-running full inventory discovery

## Endpoint Contract Recommendations

All endpoints are **POST** and return snapshot metadata so callers can reason about freshness and cache age.

### 1) Serving Group IDs
**POST** `/cmts/servingGroup/get/ids`

Returns the SG identifiers currently known to the instance (and their freshness).

Recommended response includes:
- `sg_ids`
- `snapshot.timestamp`
- `snapshot.age_seconds`
- `snapshot.source` (`config`, `discovery`, `cache`)
- `snapshot.owner_id` or `snapshot.worker_id` (optional but useful for debugging)

### 2) Cable Modems For A Specific Serving Group
**POST** `/cmts/servingGroup/get/cableModems`

Default behavior is SG-scoped to avoid CMTS-wide payload patterns.

#### Required Behavior
- Request includes `sg_id`.
- Response returns cached modem inventory for that SG by default.

#### Recommended Request Fields
- `sg_id` (required)
- `source` (optional): `cache | live | cache_with_live_state`
  - `cache`: return last SGW snapshot
  - `live`: force a poll (privileged and rate-limited)
  - `cache_with_live_state`: cached inventory + refresh only minimal state (registration) if stale
- `min_state_freshness_seconds` (optional): if cached state is older than this, perform a light state refresh
- `include` (optional): field groups to include (e.g., `identity`, `state`, `rf`, `timing`)
- `limit` and `cursor` (optional): pagination (recommended even per-SG for large SGs)

#### Recommended Response Metadata
- `snapshot.inventory_timestamp`
- `snapshot.state_timestamp`
- `snapshot.inventory_age_seconds`
- `snapshot.state_age_seconds`
- `snapshot.source`
- `snapshot.sg_id`
- `snapshot.worker_id`

### 3) Cable Modems For The Entire CMTS
**POST** `/cmts/cableModems/get`

This endpoint exists only for cases where CMTS-wide access is required.

Rules:
- Always paginated
- Prefer summary mode
- Live polling should be disabled by default and gated by policy

#### Recommended Request Fields
- `source`: `cache | live | cache_with_live_state` (default `cache`)
- `summary_only` (optional): if true, return per-SG counts and timestamps instead of modem objects
- `limit` and `cursor` (required unless `summary_only=true`)

### 4) Topology For A Specific Serving Group
**POST** `/cmts/servingGroup/get/topology`

Returns SG topology derived from cached DS/US/channel/modem relations.

Recommended request fields:
- `sg_id` (required)
- `source`: `cache | live` (default `cache`)
- `include` (optional): `ds`, `us`, `cm_counts`, `cm_sample`

Recommended response metadata mirrors `/get/cableModems` snapshot fields.

## Registration State: Efficient Update Options

When the only fast-changing attribute is “still registered,” avoid full rediscovery.

Preferred ordering:

- Tier A: Event-driven updates (traps/telemetry) to update registration state continuously
- Tier B: Incremental/delta polling (vendor-dependent)
- Tier C: Bounded state polling
  - Rate limit per SG
  - Cap payload size
  - Require pagination when returning modem state details
  - Keep this in the light refresh loop, not the heavy inventory loop

## Configuration Placement And Overrides

Phase 7 needs clear configuration semantics for Docker and Kubernetes.

Settings to define:
- `sgw.inventory_poll_seconds`
- `sgw.state_poll_seconds`
- Endpoint default `source` (`cache`)
- Live poll permissions and rate limits
- Pagination defaults (`limit`, max limit)
- Worker scaling policy (SG count → worker count)

Recommended placement:
- `system.json` as defaults
- Environment variables for container overrides
- Kubernetes ConfigMap for cluster overrides
- (Optional) CLI overrides for development and tests only

## Observability And Safety Requirements

Recommended minimum:
- Per-SG cache timestamps and ages
- Poll duration metrics (inventory and state)
- Error counters per SG and per poll tier
- Health endpoint (internal): number of SGWs running, last refresh times, last error, and whether this instance is leader/worker

## Phase 7 Deliverables

- SG discovery on startup and SGW lifecycle management aligned to leases
- In-memory SGW cache model (inventory + state, with timestamps and sources)
- Cache-first endpoints with:
  - SG scoping by default
  - Explicit CMTS-wide endpoint, always paginated
  - Snapshot metadata (timestamps and ages)
  - Optional live refresh mode with policy gates
- Tests covering:
  - Cache-default behavior for each endpoint
  - State freshness gating and refresh paths
  - Pagination and summary-only behavior for CMTS-wide modem queries
  - SGW lifecycle behavior on lease acquire/release transitions
