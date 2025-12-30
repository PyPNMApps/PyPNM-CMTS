# PyPNM-CMTS Phase 6.2 Burndown

## Objective
Deliver a read-only operational status endpoint for process visibility and deterministic, contract-stable responses.

## Completed Items
- /ops/status endpoint implemented (GET)
- Router/service split enforced for operational routes
- Contract tokens centralized as enums for status/readiness values
- Deterministic worker sorting for /ops/status
- Fallback process discovery requires exact --election-name match
- pid_records_missing, pid_records_stale, fallback_used surfaced in response
- Tests added for /ops/status (pidfiles, stale/missing, fallback)
- Docs updated with /ops/status usage, response fields, and fallback notes

## Acceptance Criteria
- /ops/status returns 200 with a structured JSON payload
- Controller and worker pidfile visibility included
- Deterministic ordering of workers in response
- Fallback discovery only uses exact --election-name match
- Tests for /ops/status pass

## Open Items
- None
