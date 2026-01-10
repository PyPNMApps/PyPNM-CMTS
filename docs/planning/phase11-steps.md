# Phase 11 Steps Tracker (PyPNM-CMTS)

This document is a step-by-step tracker for **Phase 11** work in **PyPNM-CMTS**. It is intended for Codex execution sequencing and for tracking progress during implementation.

## Phase 11 Objective

Implement SG-level **RxMER** orchestration using **direct PyPNM (pypnm-docsis) service calls** (no HTTP), with a job-style lifecycle and **filesystem-backed authoritative state**.

## Locked Endpoint Contract (POST-Only)

- `POST /cmts/pnm/rxmer/sg/startCapture`
- `POST /cmts/pnm/rxmer/sg/status`
- `POST /cmts/pnm/rxmer/sg/results`
- `POST /cmts/pnm/rxmer/sg/cancel`

## Non-Negotiable Constraints

- **Filesystem authoritative state** (multi-worker safe): `.data/sg_operations/<sg_operation_id>/`
  - `state.json` (atomic overwrite)
  - `results.jsonl` (append-only per modem)
  - `cancel.flag` (cooperative cancellation)
- **Collect-first**: capture + transfer metadata only (no decode, no analysis).
- **BaseModel-first**: all message passing uses Pydantic BaseModels; dicts allowed only for short-lived internal glue.
- **Epoch timestamps** in persisted artifacts; ISO-8601 only at response boundaries.
- Strict typing: no `Dict/List/Tuple/Union` imports; use built-in generics and `|`. Avoid `Any` unless isolated and unavoidable.
- Router thin; business logic in `service.py` and shared modules.
- No DB. No SNMP logic re-implementation in PyPNM-CMTS.
- Preserve whitespace/alignment; do not auto-format; no Ruff ignores without approval.
- Any touched/new file must update SPDX year to **2026** (or **2025-2026** range).
- Tests + docs are mandatory for completion; docs must include Mermaid lifecycle diagram; do not edit `mkdocs.yml`/nav unless explicitly requested.
- End of implementation: generate/update an agent review bundle with full contents of all touched files.

## Step Tracking

Use the checklist below to track Phase 11 progress. Do not mark items complete until tests and docs for the step are in place.

### Step 1: Baseline Discovery And Alignment

- [ ] Identify the correct existing route tree location for CMTS/PNM RxMER SG endpoints.
- [ ] Identify existing response maps (`JSON_ONLY_FAST_API_RESPONSE`, `FAST_API_RESPONSE`) and router wrapper conventions in this repo.
- [ ] Identify the correct docs location for new endpoint documentation (do not create parallel structures).
- [ ] Identify the SGW inventory access point (existing adapter/service) that returns modem membership for an `sg_id`.

Acceptance Criteria:
- A short notes section (in the Codex response) listing discovered module paths and where Phase 11 code will land.
- No code changes.

### Step 2: Operation Models (BaseModels Only)

- [ ] Create operation enums and BaseModels for:
  - operation identity (sg_operation_id, sg_id, operation_type)
  - lifecycle status enum (PENDING/RUNNING/CANCEL_REQUESTED/CANCELED/COMPLETED/FAILED)
  - persisted state model (`state.json`)
  - status response summary model (aggregate counters only)
  - start/status/results/cancel request models
  - per-modem JSONL record model

Acceptance Criteria:
- All public models are Pydantic BaseModels with one-line `Field(..., description="...")`.
- All timestamps stored as epoch seconds in persisted models.
- No generic container imports.
- SPDX year rules followed for any new file.

### Step 3: Filesystem Store (Authoritative State)

- [ ] Implement an `OperationStore` responsible for:
  - operation directory creation
  - atomic `state.json` updates (temp write + rename)
  - append-only `results.jsonl` writer (flush per record)
  - cancel flag read/write (`cancel.flag`)
  - safe read helpers with clear error surfaces (BaseModel parsing)

Acceptance Criteria:
- State is always recoverable from disk (no reliance on memory).
- Atomic write strategy in place for `state.json`.
- JSONL append is stable for large modem counts.
- Epoch timestamps preserved.

### Step 4: Operation Manager (Service-Layer API)

- [ ] Implement `OperationManager` (or equivalent) that provides:
  - `startCapture` orchestration kickoff (creates operation + schedules background runner)
  - `status` (reads state from disk, aggregate only)
  - `results` (summary aggregation or JSONL file response)
  - `cancel` (writes cancel.flag + updates state)

Acceptance Criteria:
- All method inputs/outputs use BaseModels (no dict contracts).
- Multi-worker safety: status/results/cancel work even if in-memory registry is empty.
- No router logic leaks into manager.

### Step 5: Background Execution Runner Base

- [ ] Implement a reusable runner base that:
  - updates state counters safely
  - persists progress frequently enough for status polling
  - checks cancellation cooperatively (cancel.flag) between work units
  - standardizes per-modem result append records

Acceptance Criteria:
- Cooperative cancellation behavior defined and testable.
- No blocking sleeps in request paths.
- Clear separation between runner and FastAPI layers.

### Step 6: SGW Inventory Adapter Boundary

- [ ] Implement or wire a single adapter/service boundary that returns a typed BaseModel list of modems for `sg_id`:
  - MAC
  - IP (if present)
  - registration/operational state (or enough data to gate eligibility)

Acceptance Criteria:
- Adapter returns BaseModels (no dict lists).
- Adapter is mockable for pytest without external dependencies.

### Step 7: RxMER SG Operation Runner (Collect-First)

- [ ] Implement the RxMER job runner with staged pipeline:
  1) SGW discovery (typed models)
  2) eligibility gate (registered + IP + include/exclude)
  3) bounded concurrency precheck fanout:
     - `CableModemServicePreCheck(..., validate_ofdm_exist=True).run_precheck()`
  4) bounded concurrency capture fanout:
     - `CmDsOfdmRxMerService.set_and_go(interface_parameters=...)`
  5) persist JSONL per modem stage/outcome + capture metadata
  6) honor `cancel.flag`

Acceptance Criteria:
- No PyPNM FastAPI calls; direct class calls only.
- Collect-first: capture + transfer metadata only (no decode/analysis).
- Concurrency defaults implemented via named constants (no magic numbers).
- Retries are bounded and recorded per modem.

### Step 8: FastAPI Endpoints (Router Thin)

- [ ] Add route group implementing the locked endpoints:
  - `POST /cmts/pnm/rxmer/sg/startCapture`
  - `POST /cmts/pnm/rxmer/sg/status`
  - `POST /cmts/pnm/rxmer/sg/results`
  - `POST /cmts/pnm/rxmer/sg/cancel`
- [ ] Ensure decorators include shared responses map (`JSON_ONLY_FAST_API_RESPONSE` or `FAST_API_RESPONSE` as applicable).
- [ ] Ensure request/response models are BaseModels.

Acceptance Criteria:
- Router contains routing glue only; no business logic or helper functions.
- Service layer owns all orchestration details.
- Results endpoint supports summary and JSONL file response without returning a massive JSON.

### Step 9: Pytests (Mandatory)

- [ ] Add pytest coverage with tmp_path filesystem store:
  - start creates directory + initial state
  - status returns aggregate counters
  - cancel writes flag and transitions to CANCEL_REQUESTED
  - runner honors cancel.flag and finalizes CANCELED
  - results.jsonl contains one record per modem (or per stage, if designed that way)
- [ ] Mock PyPNM boundaries:
  - `CableModemServicePreCheck.run_precheck()`
  - `CmDsOfdmRxMerService.set_and_go()`
- [ ] Mock SGW adapter boundary.

Acceptance Criteria:
- Tests run without real CMTS/modems/network.
- No deprecation warnings from pytest/ruff (treat warnings as failures).
- Coverage includes cancellation and persistence behavior.

### Step 10: Documentation + Definitions

- [ ] Add endpoint documentation in the correct existing docs location:
  - request/response schemas
  - lifecycle semantics
  - payload sizing strategy (aggregates in status; JSONL for results)
  - cancellation semantics
- [ ] Add Mermaid lifecycle diagram:
  - startCapture → poll status → results or cancel
- [ ] If new terms are introduced, update `docs/definition/index.md` alphabetically.

Acceptance Criteria:
- Markdown renders in MkDocs and GitHub.
- No emojis in docs.
- Do not modify `mkdocs.yml` or nav unless explicitly requested.

### Step 11: Agent Review Bundle (Mandatory)

- [ ] Create/update a single agent review bundle file that concatenates the full contents of every touched file.
- [ ] Ensure the bundle reflects all subsequent edits (regenerate if anything changes).

Acceptance Criteria:
- Bundle follows existing repo practice under `tools/agent-review/`.
- Bundle includes `# FILE: <path>` headers and full file contents.

## Notes

- Phase 11 is CMTS-side orchestration only. If a missing capability is identified in PyPNM, stop and propose PyPNM changes explicitly before proceeding.
- Do not mark phase burndown checkmarks automatically; code written does not imply acceptance.
