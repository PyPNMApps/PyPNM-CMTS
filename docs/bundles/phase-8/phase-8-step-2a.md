# Phase 8 · Step 2a Bundle Report

## Goal
Implement canonical CMTS request models and wire them into the pilot endpoints for serving-group ids and cable modem membership, with deterministic filter behavior and unit coverage.

## Summary of changes
- Added canonical CMTS request models with normalization and selection helpers.
- Wired serving-group ids and cable modem endpoints to the canonical request envelope while preserving legacy sg_id support.
- Added unit tests for request model validation and endpoint filter semantics (SG and MAC filters).

## Files changed
- docs/architecture/schema/cmts-request.md
- docs/planning/phase8.md
- docs/planning/phase8-burndown.md
- src/pypnm_cmts/api/common/cmts_request.py
- src/pypnm_cmts/api/routes/serving_group/router.py
- src/pypnm_cmts/api/routes/serving_group/schemas.py
- src/pypnm_cmts/api/routes/serving_group/service.py
- tests/test_cmts_request_models.py
- tests/test_sgw_endpoints.py

## Tests run
- /home/dev01/Projects/PyPNM-CMTS/.env/bin/python -m py_compile src/pypnm_cmts/api/common/cmts_request.py src/pypnm_cmts/api/routes/serving_group/schemas.py src/pypnm_cmts/api/routes/serving_group/service.py src/pypnm_cmts/api/routes/serving_group/router.py tests/test_sgw_endpoints.py tests/test_cmts_request_models.py
- /home/dev01/Projects/PyPNM-CMTS/.env/bin/python -m pytest -q tests/test_cmts_request_models.py tests/test_sgw_endpoints.py

## Results / Notes
- py_compile succeeded.
- pytest: 25 passed.
- Follow-on: extend canonical request schema to remaining endpoints in Phase 8 Step 3.
