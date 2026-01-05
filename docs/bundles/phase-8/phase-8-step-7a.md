# Phase 8 · Step 7a Bundle Report

## Goal
Harden the live CMTS pytest lane with a live_cmts marker, shared gating, and alias-safe sysDescr assertions.

## Summary of changes
- Added live_cmts marker while keeping live as a backward-compatible alias.
- Updated live test gating to skip both live and live_cmts markers unless enabled.
- Switched sysDescr live assertions to Pydantic model validation for alias-safe is_empty checks.
- Updated live test docs and Phase 8 burndown status for Step 7a.

## Files changed
- docs/api/fast-api/operational.md
- docs/planning/phase8-burndown.md
- pyproject.toml
- tests/conftest.py
- tests/live/test_live_system_endpoints.py

## Tests run
- /home/dev01/Projects/PyPNM-CMTS/.env/bin/python -m py_compile tests/conftest.py tests/live/test_live_system_endpoints.py
- /home/dev01/Projects/PyPNM-CMTS/.env/bin/python -m pytest -q
- /home/dev01/Projects/PyPNM-CMTS/.env/bin/python -m pytest -q tests/live/test_live_system_endpoints.py

## Results / Notes
- py_compile succeeded.
- Full suite: 291 passed, 10 skipped.
- Live tests skipped cleanly without --run-live or PYPNM_CMTS_RUN_LIVE=1.
- Live_cmts runs were not executed because live env was not configured.
