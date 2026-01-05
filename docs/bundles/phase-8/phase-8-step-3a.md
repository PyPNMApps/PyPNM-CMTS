# Phase 8 · Step 3a Bundle Report

## Goal
Expand canonical CMTS request schema support to the remaining serving-group endpoints, enforce topology selection rules, and align endpoint docs/tests.

## Summary of changes
- Updated serving-group topology request schema to require exactly one SG via the canonical cmts envelope while preserving legacy sg_id.
- Updated serving-group topology endpoint tests for empty, multi-SG, and single-SG behavior under the canonical envelope.
- Updated serving-group topology documentation to reference the canonical envelope and document topology-specific constraints.

## Files changed
- docs/api/fast-api/serving-group.md
- src/pypnm_cmts/api/routes/serving_group/schemas.py
- tests/test_sgw_endpoints.py

## Tests run
- /home/dev01/Projects/PyPNM-CMTS/.env/bin/python -m py_compile src/pypnm_cmts/api/routes/serving_group/schemas.py tests/test_sgw_endpoints.py
- /home/dev01/Projects/PyPNM-CMTS/.env/bin/python -m pytest -q tests/test_sgw_endpoints.py

## Results / Notes
- py_compile succeeded.
- pytest: 19 passed.
- Follow-on: extend canonical request schema to non-serving-group endpoints in Step 4.
