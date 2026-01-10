<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Maurice Garcia -->

Phase 11 · Step 2 · Generic SG Operation Foundation (Models + FS Store + Thin POST Endpoints) + RxMER Wiring Only

Implement Phase 11 Step 2 in the PyPNM-CMTS repo ONLY. One step at a time: do not advance to any later steps until Step 2 is complete and reviewed.

Before writing code, VERIFY whether AGENTS.md already contains the “Symbol Map (PyPNM Reuse Index)” section and the “BaseModel-first / avoid dicts / avoid generics” guidance. If any part is missing, UPDATE AGENTS.md in this same step to include it (minimal change only, preserve style).

Critical Coding Rules (Must Follow)
- Avoid generics and generic container imports: NO Dict/List/Tuple/Union. Use built-ins (list, dict) and |.
- Use semantic type aliases where possible (prefer src/pypnm_cmts/lib/types.py and pypnm.lib.types).
- Prefer Pydantic BaseModel for any public/stateful structure and any message passing (requests, responses, operation state, store I/O).
- dicts are allowed ONLY for short-lived internal glue (e.g., json dump/load boundaries). If a public method would accept/return a dict, replace it with a BaseModel.
- Router files must be thin; all logic in service/store layers.
- Do NOT call PyPNM FastAPI HTTP endpoints. Reuse PyPNM engine classes only (later steps).
- Any cable-modem interaction (L1/L2/L3, SNMP, reachability, capture, polling) MUST remain in PyPNM (later steps). Step 2 has NO CM interaction.
- Preserve whitespace/alignment; do not auto-format. Ruff clean. Strict typing; avoid Any.
- Update SPDX header years to 2026 (or 2025-2026) on any touched file per repo policy.
- POST-only for these Phase 11 SG endpoints:
  /cmts/pnm/rxmer/sg/startCapture
  /cmts/pnm/rxmer/sg/status
  /cmts/pnm/rxmer/sg/results
  /cmts/pnm/rxmer/sg/cancel

Step 2 Objective (Reusable Foundation First)
This step lays the reusable job/orchestration foundation for multiple future PNM operations. RxMER is the first consumer, but generic-first code reuse in PyPNM-CMTS is mandatory.

Do NOT implement SGW fanout, precheck, capture, or any PyPNM engine calls in this step.

Reuse-First Requirement (Critical)
- Build a GENERIC operation framework under:
  src/pypnm_cmts/api/common/operations/
  (models + filesystem store + shared helpers)
- RxMER route/service must only “wire” to the generic framework using RxMER request schemas and RxMER endpoint paths.
- Do NOT create RxMER-only duplicates of generic concerns (operation state, counters, filesystem layout, JSONL writer, cancellation).
- If a model/store/helper is reusable across future PNM jobs, it MUST live under api/common/operations/ and be composed by RxMER schemas.

Repo Placement Constraints (Verified)
- RxMER route placement: src/pypnm_cmts/api/routes/pnm/rxmer/
- Routers: class-based wrapper with APIRouter + _register_routes() and module-level router export.
- Shared responses: JSON_ONLY_FAST_API_RESPONSE.
- Docs: docs/api/fast-api/pnm-rxmer.md exists and follows repo conventions.
- Symbol map must be respected:
  tools/agent-review/phase11-pypnm-reuse-symbol-table.md

Schema Contract (Must Match Exactly)
Request JSON (empty list semantics):
- cmts.serving_group.id: list; empty [] means all SGs
- cmts.cable_modem.mac_address: list; empty [] means all modems in targeted SGs
- cmts.cable_modem.pnm_parameters.tftp.ipv4/ipv6: null means use PyPNM defaults; blank string invalid
- cmts.cable_modem.pnm_parameters.capture.channel_ids: list; empty [] means all channels
- cmts.cable_modem.snmp.snmpV2C.community: string or null; null uses PyPNM defaults; blank string invalid
- execution: max_workers, retry_count, retry_delay_seconds, per_modem_timeout_seconds, overall_timeout_seconds
Important: Preserve JSON casing (snmpV2C). Validate numeric fields (>= 0 where applicable; timeouts > 0).

Type Reuse Requirements
- Use PyPNM types where appropriate:
  - from pypnm.lib.types import MacAddressStr, InetAddressStr, IPv4Str, IPv6Str, TransactionId, OperationId, FileNameStr
  - from pypnm.api.routes.common.service.status_codes import ServiceStatusCode
- Prefer composing PyPNM schema models where feasible:
  - TftpConfig, PnmCaptureConfig, SNMPConfig/SNMPv2c (for blank/null rules and casing)
- Use CMTS ID aliases from src/pypnm_cmts/lib/types.py for sg_id and operation ids if they exist; otherwise add new aliases there only when necessary.

Generic Operation Models (BaseModels) — api/common/operations/
Create reusable BaseModels:
- Operation identifier type alias for pnm_capture_operation_id (semantic alias; stored as string)
- OperationState enum (API-visible): QUEUED, RUNNING, COMPLETED, FAILED, CANCELLING, CANCELLED
  Put API-visible enums/tokens in src/pypnm_cmts/lib/constants.py.
- OperationStage enum (API-visible): ELIGIBILITY, PRECHECK, CAPTURE
  Put in constants.py.
- OperationCountersModel:
  total_modems, eligible_modems, precheck_passed, capture_started, completed, success, failed, skipped
- OperationTimestampsModel (epoch seconds only):
  created_epoch, started_epoch, updated_epoch, finished_epoch
- OperationStateModel:
  operation_id + state + counters + timestamps + request_summary (minimal BaseModel) + error_summary (optional BaseModel)

Generic Results / Linkage Models (BaseModels) — api/common/operations/
- PerModemLinkageRecordModel (for JSONL append):
  - pnm_capture_operation_id
  - sg_id
  - mac_address: MacAddressStr
  - ip_address: InetAddressStr | None
  - stage: OperationStage
  - status_code: ServiceStatusCode (do not introduce CmtsStatusCode in Step 2 unless absolutely required)
  - transaction_ids: list[TransactionId] (0..N)
  - filenames: list[FileNameStr] (0..N)
  - started_epoch, finished_epoch
  - message: str

Filesystem Layout (Authoritative)
Under: .data/sg_operations/<pnm_capture_operation_id>/
- state.json (overwrite atomically)
- cancel.flag (exists => cancel requested)
- results/
  - sg-<sg_id>.jsonl (append-only; one PerModemLinkageRecordModel per line)
No retention/cleanup in this step.

Implementation Tasks
1) Create generic operations package:
   - src/pypnm_cmts/api/common/operations/__init__.py
   - src/pypnm_cmts/api/common/operations/models.py
   - src/pypnm_cmts/api/common/operations/store.py
   store.py must be class-based with strictly typed methods returning BaseModels, not dicts.
2) Implement filesystem store methods:
   - create_operation(...)
   - load_state(...)
   - save_state_atomic(...)
   - request_cancel(...)
   - is_cancel_requested(...)
   - append_result_record(...)
   All I/O boundaries may use dict internally for json load/dump, but public methods must return BaseModels.
3) RxMER schemas (compose generic models) under:
   - src/pypnm_cmts/api/routes/pnm/rxmer/schemas.py
   Do not duplicate generic state/counters fields.
4) RxMER service.py:
   - delegates to generic store for start/status/results/cancel
   - contains NO CM logic
5) RxMER router.py:
   - 4 POST endpoints with JSON_ONLY_FAST_API_RESPONSE
   - router remains glue only

Endpoint Behavior (Step 2 Only)
- startCapture:
  - validate request model
  - allocate new pnm_capture_operation_id
  - create operation dir + initial state.json (state = QUEUED or RUNNING; choose one and document it)
  - return a response BaseModel including operation_id + initial counters/timestamps
- status:
  - load and return state.json as BaseModel
- cancel:
  - create cancel.flag + update state to CANCELLING unless terminal
  - return updated state
- results:
  - return a lightweight summary BaseModel and, if “small”, include parsed JSONL records as list[PerModemLinkageRecordModel]
  - JSON-only response; no file/streaming responses in Step 2

Tests (Mandatory in Step 2)
Add pytest coverage using tmp_path (no real .data usage):
- startCapture creates operation dir + valid state.json
- status reads and returns state
- cancel creates cancel.flag and state transitions to CANCELLING
- results returns empty summary when no JSONL exists; after appending records, returns parsed results when small
No SGW and no CM mocking needed in Step 2.

Docs (Mandatory in Step 2)
Update docs/api/fast-api/pnm-rxmer.md:
- Add SG job endpoints (start/status/results/cancel)
- Request/Response JSON examples matching schemas
- Mermaid lifecycle diagram (start -> poll -> results/cancel)
No horizontal rules.

Agent Review Bundle (Mandatory)
Create/update a tools/agent-review bundle file that concatenates full contents of all touched files, each preceded by:
# FILE: <path>

Deliverables in Codex Response
- Summary of changes + why (emphasize reusable foundation)
- List of modified files (paths only)
- Tests run (pytest) + results
- Confirm API schema/response shape changes
- Path to agent review bundle
