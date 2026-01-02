# Definitions

General definitions and naming conventions used across PyPNM-CMTS.

This file is intended to be expanded over time. When a new term is introduced (code, docs, CLI output, or tests), add it here and keep the
Table Of Contents in alphabetical order.

## Table Of Contents (Alphabetical)
- [Acronyms](#acronyms)
- [Adapter](#adapter)
- [Adapter Kind](#adapter-kind)
- [Cable Modem](#cable-modem)
- [CMTS Index](#cmts-index)
- [Command (CLI)](#command-cli)
- [Controller](#controller)
- [Coordination Election Name](#coordination-election-name)
- [Coordination Manager](#coordination-manager)
- [Coordination State Directory](#coordination-state-directory)
- [Discovery (CMTS Inventory)](#discovery-cmts-inventory)
- [Epoch Seconds](#epoch-seconds)
- [Inventory Discovery](#inventory-discovery)
- [Leader ID](#leader-id)
- [Leader TTL](#leader-ttl)
- [Lease](#lease)
- [Lease Held](#lease-held)
- [Orchestrator](#orchestrator)
- [Orchestrator Mode](#orchestrator-mode)
- [Orchestrator Run ID](#orchestrator-run-id)
- [Owner ID](#owner-id)
- [Registered Cable Modem](#registered-cable-modem)
- [Result Persistence](#result-persistence)
- [Results Root](#results-root)
- [Run](#run)
- [Run-Forever](#run-forever)
- [Serve](#serve)
- [Service Group](#service-group)
- [Service Group Descriptor](#service-group-descriptor)
- [Service Group ID](#service-group-id)
- [Service Group Shard Planner](#service-group-shard-planner)
- [Shard Mode](#shard-mode)
- [Standalone](#standalone)
- [Target Service Groups](#target-service-groups)
- [Tick](#tick)
- [Tick Index](#tick-index)
- [Tick Interval](#tick-interval)
- [Unbound Worker](#unbound-worker)
- [Uvicorn](#uvicorn)
- [Work Item](#work-item)
- [Work Result](#work-result)
- [Work Status](#work-status)
- [Worker](#worker)
- [Worker Cap](#worker-cap)
- [Zero-Touch (0T)](#zero-touch-0t)

## Terms

### Adapter
The component responsible for interacting with a CMTS (for example, via SNMP). In configuration, this is represented by `CmtsAdapterConfig` and
includes `kind`, `cmts_index`, and a human-friendly `label`.

### Adapter Kind
The adapter implementation family (for example, `snmp`). This value selects which CMTS integration backend is used.

### Cable Modem
An individual modem registered on a CMTS. In inventory output, a cable modem is represented with at least a MAC
address and may include IP addressing when available.

### CMTS Index
A numeric index selecting which CMTS entry in `system.json` is being targeted by the adapter or a service group. This allows one configuration
file to describe multiple CMTS targets.

### Command (CLI)
An explicit subcommand passed to `pypnm-cmts` that selects an execution path (for example, `run`, `run-forever`, or `serve`).

### Controller
An orchestrator mode intended to coordinate and/or influence work allocation across workers. In the current skeleton, controller ticks run
coordination but do not execute worker tests.

### Coordination Election Name
A stable string identifying the leader-election namespace in the shared coordination state. Multiple independent orchestrators can coexist by
using different election names.

### Coordination Manager
The component responsible for leader election and service-group lease acquisition/renewal across multiple orchestrator instances sharing the same
state directory.

### Coordination State Directory
The filesystem directory used for shared coordination state (leader-election records, leases, and worker result persistence). Default:
`.data/coordination`.

### Discovery (CMTS Inventory)
The process of querying a CMTS via SNMP to determine the current service group inventory and the registered cable modems per service group.

### Epoch Seconds
Numeric timestamps represented as seconds since the Unix epoch (UTC). Stored timestamps use epoch seconds; ISO-8601 conversion happens only when
displaying or returning external responses.

### Inventory Discovery
The typed result of a CMTS discovery operation, including the discovered service group identifiers and the per-SG list of registered cable
modems.

### Leader ID
A stable identifier used in leader election to represent the current leader candidate. In the current design, this is derived from `owner_id`.

### Leader TTL
The leader election time-to-live in seconds. The leader record must be renewed before it expires to retain leadership.

### Lease
A time-limited claim on a resource (in this project, typically a service group). A worker is allowed to run work for a service group only while it
holds that service group’s lease.

### Lease Held
A boolean indicating whether the current worker instance holds the lease for its service group at the time of a tick.

### Orchestrator
The top-level control loop coordinating periodic ticks. Depending on mode, it may run coordination only (standalone/controller) or coordination
plus work (worker).

### Orchestrator Mode
Execution mode for the orchestrator: `standalone`, `controller`, or `worker`. This affects which coordination and work actions are performed.

### Orchestrator Run ID
A deterministic identifier used to name and persist per-tick work outputs. In worker mode, the run id is non-empty only when the worker holds the
lease. Example format: `sg<id>_tick<6-digit-index>`.

### Owner ID
A stable identifier for the running process or container instance. Used for coordination ownership, logging, and leader-election identification.

### Registered Cable Modem
A cable modem that is currently registered to the CMTS. Discovery outputs group registered modems by service group and include the modem MAC
address and, when available, its IP address.

### Result Persistence
The convention for writing work results to disk under the coordination state directory. Work results are stored under `results/sg_<id>/` with
filenames prefixed by the run id.

### Results Root
The directory name under the coordination state directory where work results are written. Current value: `results`.

### Run
A CLI subcommand that executes exactly one orchestrator tick and prints a single JSON object describing the run result.

### Run-Forever
A CLI subcommand that executes ticks repeatedly and prints one JSON object per tick (JSONL). Optionally bounded by `--max-ticks`.

### Serve
A CLI subcommand that starts the FastAPI service via Uvicorn.

### Service Group
An operational boundary grouping cable modems and plant resources on a CMTS. The orchestrator assigns work at the granularity of a service group,
identified by `sg_id`.

### Service Group Descriptor
A configuration record describing a service group boundary, including `sg_id`, optional `name`, `cmts_index`, and whether it is enabled.

### Service Group ID
An integer identifier for a service group (`ServiceGroupId`). Used as the primary key for leasing and result directory naming.

### Service Group Shard Planner
The deterministic planner that orders enabled service groups and computes the worker count for controller planning.

### Shard Mode
The strategy used to select which service groups to target per tick when the inventory is larger than the target count. Current options:
`sequential` and `score` (placeholder).

### Standalone
An orchestrator mode where a single process performs coordination ticks without being an explicit controller or worker. In the current skeleton,
standalone does not execute worker tests.

### Target Service Groups
The effective number of service groups an orchestrator instance is intended to manage concurrently. In worker mode this is always 1. In other
modes, it is derived from configuration and capped by inventory size.

### Tick
One iteration of the orchestrator control loop. A tick triggers a coordination manager update (leader election, lease maintenance) and may trigger
work execution (worker mode only, when lease is held).

### Tick Index
A monotonically increasing 1-based counter for ticks within a run loop. In the run result model, `0` indicates unset; emitted ticks are 1-based.

### Tick Interval
The configured delay between ticks in continuous mode (seconds). This value must be positive and must be less than both the leader TTL and lease
TTL.

### Unbound Worker
A worker started without `--sg-id` that requests leases for the enabled inventory each tick. Work execution and persistence are still gated by
the leases acquired in that tick.

### Uvicorn
The ASGI server used to run the FastAPI application for PyPNM-CMTS.

### Work Item
A record describing a specific test execution request for a service group, including `sg_id`, `test_name`, and `run_id`.

### Work Result
The output record for a work item execution, including `status`, `duration_seconds`, and optional `error_message`.

### Work Status
An enumeration describing the outcome of work execution: `SUCCESS`, `FAILED`, or `SKIPPED`.

### Worker
An orchestrator mode where the instance targets a specific service group (`--sg-id`). The worker executes tests only when it holds the lease for
that service group.

### Worker Cap
An optional configuration value limiting the number of worker processes/replicas allowed to participate (0 means no cap). This is a
planning/configuration primitive; enforcement may be added later.

### Zero-Touch (0T)
The target operational model where service group inventory is discovered automatically and workers self-assign work via coordination leases,
without manual per-worker SG configuration.

## Acronyms

| Acronym | Meaning |
|---------|---------|
| 0T | Zero-Touch |
| API | Application Programming Interface |
| CLI | Command Line Interface |
| CM | Cable Modem |
| CMTS | Cable Modem Termination System |
| DB | Database |
| DOCSIS | Data Over Cable Service Interface Specification |
| DS | Downstream |
| FN | Fiber Node |
| HTTP | Hypertext Transfer Protocol |
| HTTPS | Hypertext Transfer Protocol Secure |
| ICMP | Internet Control Message Protocol |
| ID | Identifier |
| IP | Internet Protocol |
| JSON | JavaScript Object Notation |
| JSONL | JSON Lines (one JSON object per line) |
| K8 | Kubernetes |
| MAC | Media Access Control |
| MD | MAC Domain |
| MIB | Management Information Base |
| OID | Object Identifier |
| PNM | Proactive Network Maintenance |
| QoS | Quality of Service |
| SG | Service Group |
| RCC | Receive Channel Configuration |
| RCP | Receive Channel Profile |
| RCS | Receive Channel Set |
| REST | Representational State Transfer |
| SG | Service Group |
| SMB | Server Message Block |
| SNMP | Simple Network Management Protocol |
| SSL | Secure Sockets Layer |
| TTL | Time To Live |
| TCS | Transmit Channel Set |
| US | Upstream |
