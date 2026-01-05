# Phase 8 · Step 6a Bundle Report

## Goal
Add an opt-in live CMTS pytest lane for system endpoints and ensure it is skipped by default.

## Summary of changes
- Added live test harness with --run-live flag and PYPNM_CMTS_RUN_LIVE env gating plus required env validation.
- Added live system endpoint tests that use real SNMP calls and skip unless enabled.
- Documented how to run live tests and updated Phase 8 burndown to reflect Step 6a completion.

## Files changed
- docs/api/fast-api/operational.md
- docs/planning/phase8-burndown.md
- pyproject.toml
- tests/conftest.py
- tests/live/test_live_system_endpoints.py

## Tests run
- /home/dev01/Projects/PyPNM-CMTS/.env/bin/python -m py_compile tests/conftest.py tests/live/test_live_system_endpoints.py
- /home/dev01/Projects/PyPNM-CMTS/.env/bin/python -m pytest -q tests/live/test_live_system_endpoints.py
- /home/dev01/Projects/PyPNM-CMTS/.env/bin/python -m pytest -q

## Results / Notes
- py_compile succeeded.
- Live tests skipped by default without --run-live or PYPNM_CMTS_RUN_LIVE=1.
- Full test suite: 291 passed, 10 skipped.
- Live topology test accepts UNREACHABLE_SNMP when topology results are empty.
