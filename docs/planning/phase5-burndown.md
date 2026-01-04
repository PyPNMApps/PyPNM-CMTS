# PyPNM-CMTS Phase 5 Burndown Close-Out

## Summary

Phase 5 focused on production-safe process control (`ps` and `stop`), runtime-owned PID publishing, and operationally safe fallback discovery. The CLI now reports accurate PID record state and can stop processes even when they were launched outside the CLI, while enforcing `--election-name` for safe fallback behavior.

## What Changed

### CLI
- `pypnm-cmts ps` reports `pid_records_missing`, `pid_records_stale`, and `fallback_used` accurately.
- Fallback discovery uses exact `--election-name` matches and ignores processes without the flag.
- `pypnm-cmts stop` uses PID files as advisory, dedupes running PIDs, and enforces `--election-name` when PID records are missing or stale.

### Runtime
- PID file creation/removal moved into `CmtsOrchestratorRuntime` so PID records exist even when started outside the CLI.
- Workers receive `sg_id` so they publish `worker_<sg>.pid` consistently.

### Harness
- `tools/system-test/p5-coordination-harness.sh` starts controller and workers using discovered SG IDs.
- Default state directory is `.state` (override via `--state-dir`).

### Docs
- CLI docs clarify fallback requirements for `--election-name` and PID namespace constraints for containers.

### Tests
- Added and updated tests for fallback empty, stale pidfiles, SIGKILL escalation, exact election-name match, and ignoring missing flags.
- Local run: `tests/test_cli_control.py` passed (12 tests).

## Acceptance Criteria Status

- Process discovery and stop work for CLI and non-CLI launched processes: Met
- PID publishing owned by runtime lifecycle: Met
- Safe fallback discovery with exact election-name match: Met
- CLI requires `--election-name` when PID records are missing or stale: Met
- Harness supports default state directory: Met

## Real-System Validation Notes

Observed on a CMTS with SG IDs 3147266 and 3213825:

1) Start controller and workers with the harness.
2) Verify `pypnm-cmts ps` shows controller and worker PID records under `<state_dir>/pids`.
3) Confirm processes are running and the harness reports STARTED.
4) Stop via harness or `pypnm-cmts stop` and confirm processes exit and PID files are removed.

## Known Follow-Ups

- The `PnmFileRetrieval.retrieval_method.methods.tftp.remote_dir` warning originates in pypnm and is out of Phase 5 scope. Track in a later cleanup.
