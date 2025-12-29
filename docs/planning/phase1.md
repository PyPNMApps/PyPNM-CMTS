# Phase-1 — Discovery (Standalone / Option-A)

## Phase-1 Goal

Phase-1 establishes read-only CMTS discovery for PyPNM-CMTS, targeting a single CMTS instance using standard SNMP, with Cisco CBR8 as the first concrete implementation.

The outcome of Phase-1 is a typed discovery snapshot that answers:

* What CMTS am I talking to?
* What Service Groups (SGs) exist on this CMTS?
* Which Cable Modems belong to each SG, and what is their basic state?

Phase-1 is strictly foundational. It enables later orchestration but does not perform it.

## Explicitly In Scope

* CMTS identity discovery (sysDescr, sysObjectID, sysName)
* Service Group enumeration (CBR8 first)
* Cable Modem inventory per Service Group
* Typed BaseModel outputs
* CLI access to discovery
* Pytest coverage for all new behavior
* Ruff compliance

## Explicitly Out of Scope

* Orchestration loops
* Worker scheduling or execution
* Thread pools or async runtime management
* Persistence (DB, state store, long-term files)
* Kubernetes or container orchestration
* Multi-CMTS coordination

## Architectural Positioning

Phase-1 operates entirely in Option-A (standalone) mode.

* One PyPNM-CMTS process
* One CMTS
* One discovery snapshot per invocation

The design must remain Kubernetes-migratable, but no K8 primitives are introduced in this phase.

## Phase-1 Burndown Checklist

### 1. CMTS Foundation (Pre-Discovery Refactor)

Purpose: clean up early prototype code so discovery is safe, testable, and extensible.

* Cmts class cleaned of cable-modem residue
* No MAC-based identity logic in Cmts
* No `exit(1)` in library code (exceptions only)
* SNMP client injection supported for testing
* Snake_case method naming normalized
* Ruff + pytest passing

### 2. Discovery Data Models

All models must be strict Pydantic BaseModel types with one-line Field(...) declarations.

* CmtsIdentityModel

  * sysDescr
  * sysObjectID
  * sysName (optional)
* ServiceGroupModel

  * sg_id
  * name (optional)
  * metadata (optional, vendor-specific)
* CableModemModel

  * mac_address
  * ip_address (optional)
  * operational_status
* DiscoverySnapshotModel

  * identity
  * service_groups
  * modems_by_service_group
  * timestamp

### 3. CMTS Operations (CBR8 First)

Extend CmtsOperation with read-only discovery methods:

* get_identity()
* list_service_groups()
* list_modems(sg_id)

Notes:

* SNMP logic must reuse PyPNM where possible
* Vendor-specific behavior (CBR8) is allowed here
* Fallback behavior must exist if SG enumeration is unavailable

### 4. Discovery Service Layer

* Single discovery entry point that:

  * calls CMTS operations
  * assembles a DiscoverySnapshotModel
* No persistence
* No background execution
* No retries beyond what SNMP already provides

### 5. CLI Integration

* Add a discovery CLI command (read-only)
* Output:

  * summary counts to console
  * optional JSON snapshot output
* CLI must enforce required arguments cleanly

### 6. Testing (Mandatory)

* Pytest coverage for:

  * model validation
  * SG fallback behavior
  * SNMP failure handling (mocked)
* Tests must not require live CMTS access
* Strict typing enforced in tests
* Ruff must pass with zero errors

## Phase-1 Exit Criteria

Phase-1 is complete when:

* A discovery snapshot can be generated for a CBR8 CMTS
* All outputs are typed BaseModels
* Pytest and Ruff pass cleanly
* No orchestration or execution logic exists
* Burndown items are explicitly marked complete only when approved

## Phase-1 Output Artifact

Primary artifact produced by Phase-1:

* Discovery Snapshot

  * Suitable for:

    * inspection
    * debugging
    * feeding Phase-2 orchestration logic
  * Not persisted automatically
