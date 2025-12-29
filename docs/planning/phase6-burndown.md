# PyPNM-CMTS Phase 6 Burndown

## Objective

- Make FastAPI the primary operational interface for health, status, and telemetry.
- Provide clear, queryable SG worker status and inventory state for operators.
- Add API-driven verification paths for system tests.
- Maintain CLI as a troubleshooting tool, not the primary control plane.

## Non-Goals

- No expansion of SNMP feature surface beyond stability needs.
- No major refactors of orchestration or coordination.
- No new coordination backends in this phase.

## Deliverables

- Health and readiness endpoints with version information.
- Orchestrator status endpoint exposing controller/worker identity and state_dir metadata.
- Inventory and SG worker status endpoints with deterministic ordering.
- Tick telemetry endpoints returning recent summaries.
- System-test harness updates using API-driven validation.
- Documentation for production use and operator workflows.

## Milestones

### M1: Operational API Skeleton

Description
- Provide minimal health and status endpoints for controller/worker processes.

Acceptance Criteria
- Endpoints available: `/healthz`, `/readyz`, `/version`, `/status`.
- Status includes election_name, state_dir, and PID record indicators.

Tasks
- Add API route models for process status.
- Add controller/worker identification in responses.

Risks/Notes
- Ensure endpoints remain read-only and do not alter orchestration.

### M2: Observability And Tick Telemetry

Description
- Expose last N tick summaries for controller and workers.

Acceptance Criteria
- Endpoint returns deterministic ordering and bounded history.
- Responses include SG mapping and work_results summary counts.

Tasks
- Define telemetry models.
- Persist and read recent tick history (bounded, no heavy storage).

Risks/Notes
- Avoid large payloads and unbounded growth.

### M3: Control-Plane Actions (Safe)

Description
- Provide safe, bounded actions for stop or reload requests.

Acceptance Criteria
- Actions are guarded, documented, and do not bypass system-level orchestration.
- Clear return codes and audit logging.

Tasks
- Define API action endpoints and models.
- Restrict actions to local process context only.

Risks/Notes
- Ensure actions do not conflict with systemd/Kubernetes ownership.

### M4: System-Test Harness And Docs

Description
- Provide API-driven verification flows and production guidance.

Acceptance Criteria
- System-test harness verifies health/status/telemetry via API.
- Docs include container and Kubernetes operator guidance.

Tasks
- Update harness scripts for API checks.
- Update docs for production workflows.

Risks/Notes
- Keep tests deterministic and avoid external dependencies.

## Sequence / Ordering

1) M1 to establish API surface and models.
2) M2 for telemetry and SG worker visibility.
3) M3 for safe control-plane actions.
4) M4 to validate and document production workflows.
