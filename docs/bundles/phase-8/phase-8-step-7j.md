# Phase 8 · Step 7j

Goal
Update the /cmts/servingGroup/get/cableModems schema and behavior to use cmts.serving_group.id list semantics with grouped results, and align tests and docs.

Summary of changes
- Reworked cable modems service logic to group by sg_id with per-group pagination and cache-first behavior
- Updated serving-group endpoint documentation for the new request/response contract
- Updated unit and integration tests to reflect grouped responses and new request shape

Files changed
- src/pypnm_cmts/api/routes/serving_group/service.py
- tests/test_sgw_endpoints.py
- tests/test_serving_group_cache_service.py
- tests/test_sgw_store_aliasing.py
- tests/integration/test_endpoints_live.py
- docs/api/fast-api/serving-group.md

Tests run
- /home/dev01/Projects/PyPNM-CMTS/.env/bin/python -m pytest -q tests/test_sgw_endpoints.py tests/test_serving_group_cache_service.py tests/test_sgw_store_aliasing.py

Results / Notes
- 18 passed in 2.42s
- Live integration tests were updated for the new request shape but remain opt-in via pytest configuration
