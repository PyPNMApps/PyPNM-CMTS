# PyPNM-CMTS Architecture And Implementation Burndown

This document defines the **software-centric architecture**, execution modes, and
a **deterministic implementation checklist** for PyPNM-CMTS.

The goal is to support a **Standalone-first** deployment model that can later
migrate cleanly to **Kubernetes** without redesign.

## Architecture Overview

PyPNM-CMTS is designed to service **one CMTS instance** and dynamically discover
Service Groups (SGs) and Cable Modems using SNMP.

The system is divided into four logical layers:

1. Discovery & Control Plane
2. Scheduling & Execution
3. Persistence & Indexing
4. API & Observability

All layers are implemented in Python and rely on **filesystem-based persistence**.
No database is used.

## Execution Modes

### Standalone Mode
- One process
- Controller + SG workers + API
- In-process concurrency
- File-based coordination

### Controller Mode
- Discovery + reconciliation only
- No workers
- Intended for Kubernetes controller pods

### Worker Mode
- One SG per process
- Intended for Kubernetes worker pods
- Polls inventory directly until message bus is introduced

## Persistence Model (No Database)

Each transaction is written to disk:

<data_root_dir>/<cmts_id>/<sg_id>/<mac>/<YYYY>/<MM>/<DD>/<transaction_id>/
  transaction.json
  results.json

An append-only JSONL index is maintained per SG/day:

<data_root_dir>/<cmts_id>/<sg_id>/index/<YYYY-MM-DD>.jsonl

## Implementation Checklist / Burndown

### Phase 0 — Contracts & Wiring
- [✅] CmtsOrchestratorSettings model implemented
- [✅] CLI mode selection added
- [✅] Adapter interface defined
- [✅] Launcher interface defined
- [✅] Coordination interfaces defined
- [✅] Docs updated (system + CLI)

### Phase 1 — Storage & Index
- [✅] Storage layout builder
- [✅] Transaction writer
- [✅] JSONL index append
- [✅] JSONL query helpers
- [✅] Pytest coverage
- [✅] Docs updated (storage)

### Phase 2 — Coordination
- [ ] File-based leader election
- [ ] File-based SG lease with TTL
- [ ] Redis placeholder
- [ ] K8 lease placeholder
- [ ] Pytest coverage
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

## Final Acceptance Checklist
- [ ] Ruff passes
- [ ] Relevant pytest tests executed
- [ ] mkdocs build --strict passes (or documented exception)
- [ ] No database introduced
- [ ] PyPNM core not modified unintentionally
- [ ] Changes aligned with AGENTS.md
