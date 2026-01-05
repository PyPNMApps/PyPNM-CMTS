# Phase 8 · Step 7b Bundle Report

## Goal
Refactor /cmts/servingGroup/get/ids to be a read-only runtime-config endpoint without requiring the CMTS request envelope.

## Summary of changes
- Added GET /cmts/servingGroup/get/ids and made POST accept empty bodies without parsing the CMTS envelope.
- Simplified get/ids service to always return discovered SG ids from runtime state.
- Updated serving-group docs to show GET usage and runtime CMTS adapter dependency.
- Updated tests to exercise GET and POST behavior without request payloads.
- Updated Phase 8 burndown status to Step 7b.

## Files changed
- docs/api/fast-api/serving-group.md
- docs/planning/phase8-burndown.md
- src/pypnm_cmts/api/routes/serving_group/router.py
- src/pypnm_cmts/api/routes/serving_group/schemas.py
- src/pypnm_cmts/api/routes/serving_group/service.py
- tests/test_sgw_endpoints.py

## Tests run
- /home/dev01/Projects/PyPNM-CMTS/.env/bin/python -m py_compile src/pypnm_cmts/api/routes/serving_group/router.py src/pypnm_cmts/api/routes/serving_group/service.py src/pypnm_cmts/api/routes/serving_group/schemas.py tests/test_sgw_endpoints.py
- /home/dev01/Projects/PyPNM-CMTS/.env/bin/python -m pytest -q tests/test_sgw_endpoints.py
- /home/dev01/Projects/PyPNM-CMTS/.env/bin/python -m pytest -q

## Results / Notes
- py_compile succeeded.
- tests/test_sgw_endpoints.py: 19 passed.
- Full suite: 291 passed, 10 skipped.
