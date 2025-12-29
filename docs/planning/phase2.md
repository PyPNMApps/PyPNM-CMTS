## Phase-2 Goals

### Objective

Implement a reliable, portable coordination layer for PyPNM-CMTS replicas so multiple instances can safely share responsibility for the same CMTS without conflicts.

### Primary Outcomes

* **Leader Election (File-Based)**

  * Guarantee at most one active leader for a given `election_name`.
  * TTL-based leadership with periodic renewal.
  * Split-brain avoidance via a filesystem lock mechanism.
  * Corruption-tolerant record handling (invalid/corrupt records do not crash; treated as absent).
  * Deterministic state persistence under `state_dir`.

* **Service Group Leases (File-Based)**

  * Allow multiple replicas to divide work by service group (SG) using TTL leases.
  * Ensure a single owner per SG at a time within an election namespace.
  * Support lease renewal, release, and status inspection.
  * Split-brain avoidance via per-SG filesystem lock.
  * Corruption-tolerant record handling (invalid/corrupt records treated as absent).

* **Coordination Models and Types**

  * Pydantic `BaseModel` result/status/record models for leader election and SG leases.
  * Strong typing via `NewType` aliases (`CoordinationElectionName`, `LeaderId`, `OwnerId`, `ServiceGroupId`).

* **Test Coverage**

  * Pytest coverage for leader election and SG lease correctness:

    * Acquire/contend
    * TTL expiry handoff
    * Renew/release
    * Busy lock behavior
    * Stale lock break
    * Corrupt/mismatched record handling
    * Input validation

### Remaining Phase-2 Scope Targets

* **Coordination Manager (Tick / Heartbeat Layer)**

  * Periodic loop to:

    * Acquire/renew leadership
    * Acquire/renew SG leases
    * Release SG leases when no longer desired
  * Status/diagnostics reporting for:

    * Leader state
    * Owned SG set
    * Conflicts / lease failures / renew failures
  * Deterministic behavior suitable for system-test harnessing.

* **Backend Placeholders**

  * Redis coordination placeholder (interface + stub implementation).
  * Kubernetes Lease coordination placeholder (interface + stub implementation).

* **Documentation**

  * Coordination architecture docs updated to reflect:

    * Records, lock paths, TTL behavior
    * Failover and stale-lock semantics
    * How SG worker count scales and how SG assignment is computed

## Phase-2 Burndown

### Done

* **File-based leader election**

  * TTL record persisted as JSON under `state_dir`
  * Lock directory protection with stale lock break
  * Validation and corrupt-record resilience
  * `try_acquire()`, `renew()`, `release()`, `status()`
* **File-based service group lease**

  * TTL record per SG persisted as JSON under `state_dir`
  * Per-SG lock directory protection with stale lock break
  * Validation and corrupt-record resilience
  * `try_acquire()`, `renew()`, `release()`, `status()`
* **Models**

  * Pydantic models for leader and lease records/status/results
  * `NewType` aliases for coordination types
* **Tests**

  * Leader election tests covering normal, contention, busy lock, stale lock, corruption/mismatch, TTL expiry
  * Service group lease tests covering same core behaviors

### In Progress / Next Up

* **Coordination Manager**

  * Add a manager component that:

    * Runs a tick loop
    * Acquires/renews leadership
    * Calculates desired SG set for the instance
    * Acquires/renews/releases SG leases accordingly
  * Add models for tick results and coordination status snapshots
  * Add pytest coverage for multi-instance behaviors (simulated clocks + shared state_dir)

### Not Started

* **Redis placeholder**

  * Define interface + stub module to preserve future backend compatibility
* **Kubernetes Lease placeholder**

  * Define interface + stub module for K8s integration path
* **Docs updated (coordination)**

  * Update `architecture.md` / coordination docs with:

    * File formats, lock semantics, TTL timing, failure modes
    * Replicas, leader behavior, SG lease behavior, worker scaling

### Deferred (Phase-3+ candidates, not required to close Phase-2 unless you decide otherwise)

* CLI / FastAPI endpoints to expose coordination status (leader + SG leases)
* Metrics / observability integration (structured logs, counters, timings)
* Hardening for cross-filesystem edge cases (NFS semantics, etc.) if needed later
