# Phase 8 · Step 7k

Goal
Remove cable_modem fields from the /cmts/servingGroup/get/cableModems request schema so OpenAPI matches the new minimal contract.

Summary of changes
- Introduced a serving-group-only envelope for the cableModems request schema
- Kept topology requests on the full CMTS envelope while ensuring cableModems OpenAPI no longer exposes cable_modem fields

Files changed
- src/pypnm_cmts/api/routes/serving_group/schemas.py

Tests run
- /home/dev01/Projects/PyPNM-CMTS/.env/bin/python -m pytest -q tests/test_sgw_endpoints.py

Results / Notes
- 14 passed in 2.53s
