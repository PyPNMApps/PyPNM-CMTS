# PyPNM-CMTS Phase 4 – Zero-Touch Worker Enablement

This Document Defines Phase 4 Goals And Deliverables With A Focus On Achieving Zero-Touch (0T) Service Group Workers.

## Table Of Contents

- [Objective](#objective)
- [Deliverables](#deliverables)
- [Acceptance Criteria](#acceptance-criteria)
- [Out Of Scope](#out-of-scope)

## Objective

Deliver Zero-Touch (0T) Inventory Discovery And Worker Enablement:

- Auto-discover Service Groups (N SGs) from the CMTS using SNMP connectivity.
- Enumerate all registered Cable Modems per SG (minimum MAC; include IP when available).
- Allow workers to operate without manual SG assignment while preserving the bound worker path for debug and
  operational override.

## Deliverables

1. **Unbound Worker Mode**
   - Allow `--mode worker` with no `--sg-id`.
   - Worker requests leases for all enabled SG IDs.

2. **Launcher And Coordination Updates**
   - Shift SG binding to per-tick assignment using `acquired_sg_ids`.
   - Maintain deterministic `tick_index` semantics.

3. **Result Model Semantics**
   - `lease_held` is true when the worker acquired at least one SG lease.
   - `run_id` is present only when work executed.
   - `work_results` is empty when no lease is held.

4. **CMTS-Based Inventory Discovery**
   - Discover SG inventory from the CMTS via SNMP (N SGs).
   - Enumerate all registered CMs per SG (MAC required; include IP when available).
   - Provide output surfaces (CLI and/or API) that show SGs and registered CMs grouped by SG.

5. **Docs**
   - Update architecture docs to state 0T as the production target.
   - Update CLI docs to describe both bound and unbound worker usage.

6. **Tests**
   - Add unit tests proving unbound worker runs with no `--sg-id` and performs no work when no lease is held.
   - Add unit tests proving lease-gated persistence for unbound workers.
   - Add discovery tests validating SG inventory and per-SG CM enumeration.

## Acceptance Criteria

- Given CMTS host + SNMP credentials, PyPNM-CMTS discovers N enabled SGs on the target CMTS.
- For each discovered SG, PyPNM-CMTS returns the full list of registered CMs.
- Unbound workers can start with `pypnm-cmts run-forever --mode worker` and safely idle when no lease is held.
- When a lease is acquired, the worker executes and persists only the SG(s) acquired for that tick.
- Bound worker path (`--sg-id`) remains supported for override and debugging.
- Validation example: the lab CMTS currently reports 2 SGs and discovery returns both.

## Out Of Scope

- Multi-node shared coordination backend migration (file-based coordination is sufficient for Phase 4).
- Large-scale refactors unrelated to discovery and worker enablement.

## Phase 4 Checklist

- [ ] Add CMTS-based SG discovery via SNMP (inventory model).
- [ ] Add per-SG CM enumeration (MAC required; IP when available).
- [ ] Expose discovery output via CLI and/or API grouped by SG.
- [ ] Preserve bound worker path while enabling unbound worker mode.
- [ ] Enforce lease-gated work execution and persistence for unbound workers.
- [ ] Add discovery and worker-mode tests covering SG and CM enumeration.
