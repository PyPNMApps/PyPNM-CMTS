# PyPNM-CMTS TODO (Phase 7.8)

Last Updated: 2026-01-05 (America/Denver)

This is the running, repo-wide TODO list for PyPNM-CMTS. Items are written so they can be checked off by Codex as work completes.

## Completed (Phase 7.7)

Phase 7.7 is closed. Archive references live at:
- docs/architecture/archive/phase-7.7/README.md

## Completed (Phase 7.8)

- [x] Phase 7.8 · Step 1: Burndown + TODO reset (2026-01-04)
- [x] Phase 7.8 · Step 2: SG discovery contract + static discovery implementation (2026-01-04)

## Open Items (Phase 7.8)

- [ ] Phase 7.8 · Step 3: SNMP discovery implementation (real)
- [ ] Phase 7.8 · Step 4: Heavy refresh inventory pipeline hardening
- [ ] Phase 7.8 · Step 5: Light refresh delta pipeline hardening
- [ ] Phase 7.8 · Step 6: SGW background scheduler/worker lifecycle hardening
- [ ] Phase 7.8 · Step 7: Endpoint refresh semantics + rate limiting validation
- [ ] Phase 7.8 · Step 8: Observability pass (structured logs, metrics stubs, readiness clarity)
- [ ] Phase 7.8 · Step 9: Load-safety pass (lock contention, deep-copy boundaries, perf sanity checks)
- [ ] Phase 7.8 · Step 10: Final QA + legacy hygiene scan + release readiness notes
- [ ] Keep AGENTS response preferences aligned with user updates (update file when requested)
- [ ] Before proposing or making PyPNM (pypnm-docsis) changes, state the plan and rationale explicitly
- [ ] Ensure any modified or newly created file updates the SPDX header year to 2026
- [ ] If a file already has a SPDX year and the year has changed, update it as a range (example: 2025 -> 2025-2026)
- [ ] When fixing an error, add or update the FAQ entry with the error and resolution

## Deferred Items

- [ ] Re-enable `tests/test_sgw_manager_refresh.py::test_sgw_manager_refresh_forever_uses_clock_and_stops` after resolving slow execution in full suite (currently skipped).
