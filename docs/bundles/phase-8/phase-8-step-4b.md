# Phase 8 · Step 4b Bundle Report

## Goal
Stabilize system endpoint request models by removing import-time schema shape changes, enforce canonical camelCase JSON examples, and extend tests for camelCase acceptance.

## Summary of changes
- Made CMTS SNMP config schema stable by defining SNMP fields unconditionally and using runtime hostname defaults.
- Updated FastAPI docs examples to use camelCase `snmpV2c` in canonical requests while keeping legacy examples intact.
- Added camelCase request coverage for system endpoint tests.

## Files changed
- docs/api/fast-api/index.md
- src/pypnm_cmts/api/common/cmts/schema.py
- tests/test_system_endpoints.py

## Tests run
- /home/dev01/Projects/PyPNM-CMTS/.env/bin/python -m py_compile src/pypnm_cmts/api/common/cmts/schema.py tests/test_system_endpoints.py
- /home/dev01/Projects/PyPNM-CMTS/.env/bin/python -m pytest -q tests/test_system_endpoints.py

## Results / Notes
- py_compile succeeded.
- pytest: 6 passed.
- Follow-on: ensure future endpoint docs align camelCase with to_camel aliases.
