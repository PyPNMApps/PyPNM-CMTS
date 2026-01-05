# Phase 8 · Step 7c

## Goal
Add a startup precheck class for CMTS ping and SNMP reachability, wire it into SGW startup for SNMP discovery mode, and add hermetic tests.

## Summary of changes
- Added CMTS startup precheck class with ping and SNMP sysDescr checks.
- Wired precheck into SGW startup for SNMP discovery mode and logged results.
- Added startup tests for precheck success and failure paths.

## Files changed
- src/pypnm_cmts/sgw/precheck.py
- src/pypnm_cmts/sgw/startup.py
- tests/test_sgw_startup.py

## Tests run
- /home/dev01/Projects/PyPNM-CMTS/.env/bin/python -m py_compile src/pypnm_cmts/sgw/precheck.py src/pypnm_cmts/sgw/startup.py tests/test_sgw_startup.py
- /home/dev01/Projects/PyPNM-CMTS/.env/bin/python -m pytest -q tests/test_sgw_startup.py

## Results / Notes
- Precheck runs only for sgw.discovery.mode == snmp and logs ping/SNMP status before discovery.
