# Phase 11 Burndown Plan (PyPNM-CMTS)

## Scope

Phase 11 implements **Serving Group (SG)** RxMER orchestration in **PyPNM-CMTS** using **direct PyPNM (pypnm-docsis) service calls** (no HTTP). The implementation must be **multi-worker safe**, **filesystem-backed**, strictly typed, and router-thin.

Key constraints:

* **POST-only** endpoints for this feature.
* **Filesystem is authoritative** for job state (`state.json`, `results.jsonl`, `cancel.flag`).
* **Collect-first** means **capture + transfer metadata only** (no decode, no analysis).
* **All message passing** uses **Pydantic BaseModel** (dict discouraged; allowed only for short-lived internal glue).
* **No DB**; no SNMP logic in PyPNM-CMTS (PyPNM remains authoritative).
* **Tests + docs mandatory**. Mermaid diagram required for orchestration lifecycle.
* **Update SPDX header years to 2026 (or 2025-2026 range)** for any touched/new file.
* Maintain repo conventions: strict typing, no generic container imports, preserve alignment, no auto-formatting, no emojis outside allowed files.

## Objective

Provide a job-style orchestration API for SG-level RxMER capture that:

* starts quickly and returns an `sg_operation_id`
* runs the job in the background with bounded concurrency
* supports polling for progress and cancellation
* persists results per modem in JSONL without large response payloads

## Phase 11 Deliverables

### 1) API Surface (POST-only, contract locked)

Implement these endpoints:

* `POST /cmts/pnm/rxmer/sg/startCapture`
* `POST /cmts/pnm/rxmer/sg/status`
* `POST /cmts/pnm/rxmer/sg/results`
* `POST /cmts/pnm/rxmer/sg/cancel`

Requirements:

* Routers are thin: routing glue only.
* All request/response bodies are Pydantic BaseModels.
* `status` returns aggregates only (no massive per-modem payload).
* `results` returns summary or JSONL file response.

### 2) Filesystem-Backed Operation Framework (Generic)

Implement reusable job framework components:

* Operation directory layout:

  * `.data/sg_operations/<sg_operation_id>/state.json`
  * `.data/sg_operations/<sg_operation_id>/results.jsonl`
  * `.data/sg_operations/<sg_operation_id>/cancel.flag`

State requirements:

* `state.json` is updated atomically.
* timestamps stored as **epoch seconds** (ISO only at response boundary).
* results are appended as **one JSON object per line** in `results.jsonl`.

Models requirements:

* Use BaseModels for:

  * operation identity, lifecycle, counters, timestamps
  * per-modem result record (JSONL line model)
  * requests/responses for all endpoints
* Avoid dict except short-lived internal glue.

### 3) RxMER SG Operation Runner (Collect-First)

Implement orchestration pipeline per operation:

Stage 0: **SG modem discovery**

* Retrieve modem list from SGW inventory/snapshot.
* Use an adapter/service to isolate SGW coupling.

Stage 1: **Eligibility gate** (fast, local)

* Must be registered/operational
* Must have IP
* Apply include/exclude scoping if provided

Stage 2: **Precheck fanout** (bounded concurrency)

* Call PyPNM:

  * `CableModemServicePreCheck(..., validate_ofdm_exist=True).run_precheck()`
* Record outcome per modem to JSONL.

Stage 3: **Capture fanout** (bounded concurrency)

* Call PyPNM:

  * `CmDsOfdmRxMerService.set_and_go(interface_parameters=...)`
* Record capture + transfer metadata only.

Cancellation:

* `cancel.flag` triggers cooperative stop:

  * stop scheduling new modem work
  * allow in-flight tasks to finish or timeout
  * finalize state to `CANCELED`

### 4) Concurrency / Retry Policy (Conservative Defaults)

Defaults (constants, no magic numbers):

* precheck concurrency: 20
* capture concurrency: 10

Retry policy:

* bounded retries aligned to PyPNM `ServiceStatusCode`
* retries tracked per-modem in result record and reflected in aggregates

### 5) Tests (pytest, mandatory)

Add pytest coverage that requires **no real CMTS**:

* startCapture:

  * creates operation directory and initial `state.json`
  * returns `sg_operation_id`
* status:

  * reads `state.json` and returns aggregates
* cancel:

  * writes `cancel.flag` and updates state
* runner:

  * persists JSONL per modem
  * transitions state through expected lifecycle
  * honors cancel.flag (ends `CANCELED`)
* concurrency:

  * verify bounded fanout behavior with deterministic mocks (no sleeps in request path)

Mock boundaries:

* `CableModemServicePreCheck.run_precheck()`
* `CmDsOfdmRxMerService.set_and_go()`
* SGW modem inventory adapter

Treat warnings (pytest/ruff deprecations) as failures.

### 6) Documentation (mandatory)

Add docs for Phase 11:

* endpoint docs for the four POST routes
* lifecycle explanation and payload sizing strategy
* cancellation semantics
* Mermaid diagram:

  * startCapture → poll status → results or cancel
* Do not modify mkdocs.yml or nav unless explicitly requested.
* No horizontal rules in Markdown.
* Update `docs/definition/index.md` if new acronyms/terms are introduced.

### 7) Agent Review Bundle (mandatory)

After completion, create/update a single agent review bundle file that concatenates the full contents of all touched files, using the repo’s existing practice under `tools/agent-review/`.

## Implementation Order (Suggested)

1. Create operation models + store (FS authoritative)
2. Add manager + base runner scaffolding
3. Wire endpoints (router thin, service heavy)
4. Implement RxMER runner stages (eligibility → precheck → capture)
5. Add tests for persistence, lifecycle, cancellation, aggregation
6. Add docs + Mermaid diagram
7. Generate agent review bundle

## Out Of Scope (Phase 11)

* decode PNM files (`CommonProcessService.process()`)
* analysis (`Analysis(...)`)
* database-backed orchestration
* Kubernetes deployment features
* adding new SNMP capabilities (must go to PyPNM, not here)


