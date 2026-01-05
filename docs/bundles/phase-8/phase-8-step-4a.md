# Phase 8 · Step 4a Bundle Report

## Goal
Expand canonical CMTS request schema support to non-serving-group endpoints and align docs/tests for system endpoints.

## Summary of changes
- Added canonical CMTS request envelope support to system endpoint request parsing while preserving legacy shape.
- Updated system service handlers to use normalized target hostname.
- Documented canonical system endpoint request bodies and legacy fallback in FastAPI index docs.
- Added hermetic system endpoint tests for canonical and legacy requests.

## Files changed
- docs/api/fast-api/index.md
- src/pypnm_cmts/api/common/cmts/schema.py
- src/pypnm_cmts/api/routes/system/service.py
- tests/test_system_endpoints.py

## Tests run
- /home/dev01/Projects/PyPNM-CMTS/.env/bin/python -m py_compile src/pypnm_cmts/api/common/cmts/schema.py src/pypnm_cmts/api/routes/system/service.py tests/test_system_endpoints.py
- /home/dev01/Projects/PyPNM-CMTS/.env/bin/python -m pytest -q tests/test_system_endpoints.py

## Results / Notes
- py_compile succeeded.
- pytest: 4 passed.
- Follow-on: update additional non-serving-group endpoints as they are introduced or refactored.
