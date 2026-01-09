# Phase 10 Goals (Codex) · PyPNM-CMTS PNM Orchestration via PyPNM

## Objective

Phase 10 delivers the “meat and potatoes” integration: PyPNM-CMTS will orchestrate PNM capture operations per Serving Group (SG) while delegating all DOCSIS/PNM capture logic to the PyPNM (pypnm-docsis) layer.

The initial target operation is **RxMER** for DOCSIS OFDM, executed concurrently across cable modems in an SG using SGW cache inventory.

## Critical Constraints

- Start with **PyPNM first**. Only after PyPNM supports the required capture contract should PyPNM-CMTS integrate it.
- Do not re-implement PyPNM SNMP/PNM logic inside PyPNM-CMTS.
- Prefer “under-the-hood” Python calls into PyPNM services over FastAPI-to-FastAPI HTTP calls unless blocked.
- All contract changes require docs updates. If a workflow needs a diagram, add Mermaid flow charts.
- Preserve strict typing and reuse patterns from PyPNM where applicable.

## Integration Strategy

### Source of PNM Capture Logic

PyPNM code to reference lives primarily under:

- `/home/dev01/Projects/PyPNM/src/pypnm/api/routes/docs/pnm`

For RxMER specifically:

- `src/pypnm/api/routes/docs/pnm/ds/ofdm/rxmer`

### Request Contract Change (PyPNM)

PyPNM currently performs PNM operations across all channels. Phase 10 introduces optional channel targeting.

Add optional channel targeting at:

- `pnm_parameters.capture.channel_ids`

The intent is that, when provided, PyPNM performs capture for only the specified channel ids. When omitted, PyPNM behavior remains unchanged (capture all channels, as today).

A future SG-level orchestration call in PyPNM-CMTS may also choose to pass `channel_ids` as a list.

## Phase 10 Deliverables

### Deliverable 1 · PyPNM RxMER Optional Channel Targeting

- Extend the PyPNM RxMER request models to accept `pnm_parameters.capture.channel_ids`.
- Implement filtering so capture can target specific channel ids.
- Maintain backward compatibility for existing request payloads.
- Add pytest coverage for:
  - Default behavior (no `channel_ids`) matches current behavior
  - Specifying `channel_ids` limits capture scope to those channels
  - Validation errors for invalid channel ids (if applicable)

### Deliverable 2 · PyPNM-CMTS Orchestration Framework (Planned After PyPNM Change)

This deliverable is deferred until PyPNM is updated.

- Build a reusable concurrent “fanout” execution abstraction for SG modem operations.
- Implement `RxMerServiceGroupCapture` as the first concrete operation using that abstraction.
- Inventory source is SGW cache (registered/online + IP/inet known).
- Initial goal is “collect first, analyze later” (store captures and return per-modem statuses).

### Deliverable 3 · Documentation Updates

- Update PyPNM docs for the RxMER request schema to include `pnm_parameters.capture.channel_ids`.
- Update PyPNM-CMTS docs when orchestration endpoints are added.
- If describing orchestration flows, include Mermaid diagrams.

## Definition of Done

- PyPNM supports `pnm_parameters.capture.channel_ids` for RxMER and remains backward compatible.
- Pytests are added and pass locally (no real CMTS required; mock where needed).
- Documentation is updated alongside the contract change.
- No unscoped refactors; changes are minimal and phase-aligned.
