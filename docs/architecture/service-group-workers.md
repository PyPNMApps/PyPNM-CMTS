# PyPNM-CMTS Architecture – Service Group Workers And Zero-Touch Operation

This Document Defines The Target ("End-Game") Architecture For PyPNM-CMTS Orchestration, Including Zero-Touch (0T)
Service Group Worker Assignment And Scale-Out Behavior.

## Table Of Contents

- [Scope](#scope)
- [End Goal](#end-goal)
- [Key Concepts](#key-concepts)
- [Execution Roles](#execution-roles)
- [Zero-Touch Worker Lifecycle](#zero-touch-worker-lifecycle)
- [Coordination And Leasing](#coordination-and-leasing)
- [Result Persistence](#result-persistence)
- [Scaling Model](#scaling-model)
- [Failure Handling](#failure-handling)
- [Configuration Expectations](#configuration-expectations)
- [SGW Discovery Modes](#sgw-discovery-modes)
- [Implementation Notes](#implementation-notes)

## Scope

This Architecture Covers The PyPNM-CMTS Orchestrator And Its Interaction With Service Groups (SGs), Including:

- How SGs Are Discovered (From Configuration And/Or CMTS Inventory).
- How Work Is Assigned To Workers Using Coordination Leases.
- How Results Are Persisted In A Deterministic, Auditable Manner.
- How Worker Count Scales With The Number Of Service Groups.

## End Goal

The Production Target Is Zero-Touch (0T) Installation And Operation:

- A Worker Does Not Require A Static `--sg-id` At Startup To Be Useful.
- Workers Self-Assign Work By Participating In Coordination Leasing.
- Adding Workers Increases Throughput Without Manual Sharding Or Per-Worker Configuration.

At The Same Time, The System Supports An Explicit (Bound) Worker Mode For Debugging, Incremental Rollout, And
Operational Override When Needed.

## Key Concepts

**Service Group (SG)**  
The Fundamental Unit Of Work Scheduling. A Worker Executes Tests For One SG Per Tick (Initial Target), Producing
Structured Results And Persisting Them Under An SG-Specific Path.

**Tick**  
A Single Iteration Of The Orchestrator: read configuration and/or inventory, execute coordination, run tests (if
assigned), persist results, and emit a JSON status snapshot.

**Lease**  
A Time-Bounded Claim Over An SG That Grants A Worker The Right To Execute Work For That SG In The Current Tick.

## Execution Roles

PyPNM-CMTS Defines Three Operational Roles:

### Standalone

- Performs Coordination And Work In A Single Process.
- Useful For Local Development And Single-Host Operation.
- Runs A Tick And May Execute Work For Any SG(s) It Acquires.

### Controller

- Primarily Runs Coordination To Assign SG Leases.
- May Be Extended To Publish Cluster-Wide Status (Future).
- Does Not Necessarily Execute Work (policy-based).

### Worker

Two Worker Variants Are Supported:

**Bound Worker (Explicit SG Assignment)**  
- Starts With `--mode worker --sg-id <id>`.
- Requests A Lease Only For That SG.
- Executes Work Only For That SG When The Lease Is Held.

**Unbound Worker (Zero-Touch)**  
- Starts With `--mode worker` (no `--sg-id`).
- Requests Leases For The Enabled SG Set.
- Executes Work For The SG(s) It Acquires In The Current Tick.

## Zero-Touch Worker Lifecycle

This Is The Intended End-State Worker Behavior:

1. **Boot**
   - Load System Configuration.
   - Build The Enabled SG Inventory.
   - Establish The Coordination State Directory (or configured state backend).

2. **Tick Start**
   - Determine The SG Candidate Set:
     - If Bound Worker: the single `sg_id`.
     - If Unbound Worker: all enabled SG IDs.
   - Submit Candidate Set To Coordination Manager.

3. **Coordination**
   - Coordination Returns `acquired_sg_ids` For The Tick.
   - If No SG Is Acquired, Worker Performs No Work And Returns A Snapshot.

4. **Work**
   - For Each Acquired SG ID (initial policy: at most one):
     - Execute The SG Test Plan.
     - Build `work_results` for that SG.

5. **Persist**
   - Persist Results Only If A Lease Was Held For That SG In The Tick.

6. **Emit**
   - Emit `OrchestratorRunResultModel` JSON including:
     - `tick_index` (coordination-driven, 1-based in-process)
     - `lease_held` (true when at least one SG lease is held)
     - `run_id` (populated only when work executed)
     - `work_results` (empty when no lease held)

## Coordination And Leasing

Coordination Is The Gate That Makes Zero-Touch Possible.

**Contract**
- Worker Submits A Candidate SG Set.
- Coordination Returns Which SGs Are Leased By This Worker In The Tick.
- Work Execution Must Be Strictly Conditioned On The Lease Result.

**Single-SG-Per-Tick Policy (Initial Target)**
- Coordination Should Prefer Assigning At Most One SG Per Worker Per Tick.
- This Matches The Deterministic Persistence Model And Simplifies Run Semantics.

**Multi-SG-Per-Tick (Future Extension)**
- Allowed Only If:
  - The Work Pipeline Can Execute SGs Independently.
  - Persistence Is SG-Scoped And Collision-Free.
  - The Result Model Clearly Represents Multi-SG Runs.

## Result Persistence

Worker Mode Persists Results Under The Coordination State Directory:

```
<state_dir>/results/sg_<sg_id>/
```

Each File Name Is Deterministic Per Tick:

```
sg<sg_id>_tick<tick_index>_<test_name>.json
```

**Invariant**
- Persistence Occurs Only When The Worker Holds The Lease For That SG In That Tick.
- If The Worker Holds No Lease, No Result Files Are Written.

## Scaling Model

PyPNM-CMTS Is Designed To Scale With The Number Of Service Groups.

### Primary Scaling Lever

**SG Worker Count**

- Increasing worker replicas increases the probability of concurrent SG lease coverage.
- Target model: 1 worker can serve multiple SGs over time; N workers can serve up to N SGs concurrently per tick.

### Practical Deployment Guidance

- If You Have `S` Enabled Service Groups, Start With `min(S, N)` Workers Where `N` Reflects Desired Parallelism.
- Zero-Touch Workers Remove The Need For Pre-Assigning SG IDs To Each Worker.

## Failure Handling

The System Must Be Safe Under Partial Failure:

- If Coordination Fails: return a status snapshot with no work executed.
- If Work Execution Fails For One SG: persist only successful results; log failure; continue operation per policy.
- If A Worker Dies Mid-Tick: leases expire via TTL; another worker can acquire the SG in a future tick.

## Configuration Expectations

Zero-Touch Still Requires A Minimal Configuration Baseline:

- Defined Service Groups (enabled/disabled) and orchestration policy (target service groups, shard mode).
- A Coordination State Directory (or future shared backend) accessible to participating workers.
- SNMP connectivity and CMTS inventory discovery prerequisites for production-grade SG enumeration.

## SGW Discovery Modes

This Section Defines How PyPNM-CMTS Determines The Initial Service Group Set At Startup.

### Static

Static Discovery Uses `CmtsOrchestrator.service_groups` entries (from config).

- Intended For Lab, CI, Or Fixed Environments.
- If The List Is Empty Or Missing, Discovery Returns No SGs.
- No SNMP Calls Are Performed.

### SNMP

SNMP Discovery Queries The CMTS For Service Group Inventory.

- Uses `CmtsOrchestrator.adapter` settings (`hostname`, `community`, `port`).
- Startup Runs A Precheck (ICMP Ping + SNMP sysDescr) Before Discovery.
- If Precheck Fails, SGW Startup Records A Failure And Skips Discovery.

### Default Behavior

If `sgw.discovery.mode` Is Missing Or Empty, The Default Is `snmp`.

### Logging

Startup Logs The Discovery Mode And The Derived SG Worker IDs:

- `SGW discovery mode: <mode>`
- `SGWorkerID: [sgw-<sg_id>, ...]`

## Implementation Notes

Serving Group Workers Maintain Cache Snapshots With Heavy And Light Refresh Lanes And Expose Cache-First Reads.

To Reach And Maintain The 0T End-State, These Design Rules Apply:

- Do Not Bind SG Assignment At Process Startup Unless Explicitly Requested.
- Treat Coordination Output As The Source Of Truth For Work Eligibility.
- Separate "Enabled Inventory" (what could be worked) From "Acquired Assignment" (what is worked this tick).
- Keep Persistence Strictly Lease-Gated To Avoid Duplicate Or Conflicting Outputs.

## Startup Integration

- On Serve Or Combined Startup, Discover The Enabled SG Set Before Spawning SGWs.
- SGW Manager Starts One Worker Per sg_id (Capped By Max Workers) And Primes Each Cache Before Readiness Is Reported.
- Cache-First API Responses Must Not Trigger Implicit SNMP Walks; Discovery + SGW Priming Are The Gate For /ops/ready.
