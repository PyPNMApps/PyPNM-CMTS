# Phase 8 · Step 7n

Goal
Replace registration_status integers with structured objects across responses, add decoding helpers, and align docs/tests with the breaking contract change.

Summary of changes
- Added DOCSIS registration status text enum and decode helper under docsis/data_type
- Introduced a shared API model for registration_status and wired it into cable modem response schemas
- Updated service mapping to emit status/text objects and refreshed docs/examples and tests

Files changed
- src/pypnm_cmts/docsis/data_type/cmts_cm_reg_state.py
- src/pypnm_cmts/docsis/data_type/__init__.py
- src/pypnm_cmts/api/common/cmts_reg_status.py
- src/pypnm_cmts/api/routes/serving_group/schemas.py
- src/pypnm_cmts/api/routes/serving_group/service.py
- docs/api/fast-api/serving-group.md
- docs/architecture/schema/cmts-request.md
- tests/test_cmts_cm_reg_state_text.py
- tests/test_sgw_endpoints.py
- tests/test_cmts_inventory_discovery.py

Tests run
- /home/dev01/Projects/PyPNM-CMTS/.env/bin/python -m pytest -q tests/test_cmts_cm_reg_state_text.py tests/test_sgw_endpoints.py tests/test_cmts_inventory_discovery.py

Results / Notes
- 18 passed in 2.48s
- registration_status is now an object with status/text tokens (breaking change)
