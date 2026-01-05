# Phase 8 · Step 5a Bundle Report

## Goal
Add CLI overrides for CM SNMP/TFTP defaults and apply them as request defaults when the canonical CMTS request omits override fields.

## Summary of changes
- Added CM override environment-backed defaults for SNMPv2c write community and TFTP IPv4/IPv6.
- Added CLI flags for CM overrides and wired serve mode to export them into runtime settings.
- Added request default application helper and unit tests for env-driven defaults and CLI overrides.

## Files changed
- src/pypnm_cmts/api/common/cmts_request.py
- src/pypnm_cmts/cli.py
- src/pypnm_cmts/config/request_defaults.py
- tests/test_cmts_request_models.py
- tests/test_cli_serve_overrides.py

## Tests run
- /home/dev01/Projects/PyPNM-CMTS/.env/bin/python -m py_compile src/pypnm_cmts/cli.py src/pypnm_cmts/api/common/cmts_request.py src/pypnm_cmts/config/request_defaults.py tests/test_cmts_request_models.py tests/test_cli_serve_overrides.py
- /home/dev01/Projects/PyPNM-CMTS/.env/bin/python -m pytest -q tests/test_cmts_request_models.py tests/test_cli_serve_overrides.py

## Results / Notes
- py_compile succeeded.
- pytest: 8 passed.
- Follow-on: wire request defaults into endpoints that consume CM override fields once implemented.
