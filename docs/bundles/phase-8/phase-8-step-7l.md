# Phase 8 · Step 7l

Goal
Populate cable modem registration status and DS/US channel set ids in SGW snapshots and cableModems responses using existing CMTS operations, and codify the PyPNM-change notification rule.

Summary of changes
- Extended CMTS discovery models to include registration status and channel set ids
- Switched inventory discovery to use getAllRegisterCm and mapped CM registration fields into snapshot data
- Wired heavy poller and cableModems response mapping to emit ds/us channel sets and registration status
- Updated tests to assert the new fields and updated AGENTS/TODO guidance for PyPNM change notifications

Files changed
- AGENTS.md
- docs/todo/todo.md
- docs/api/fast-api/serving-group.md
- src/pypnm_cmts/cmts/discovery_models.py
- src/pypnm_cmts/cmts/inventory_discovery.py
- src/pypnm_cmts/sgw/models.py
- src/pypnm_cmts/sgw/pollers/heavy.py
- src/pypnm_cmts/api/routes/serving_group/service.py
- tests/test_cmts_inventory_discovery.py
- tests/test_sgw_endpoints.py

Tests run
- /home/dev01/Projects/PyPNM-CMTS/.env/bin/python -m pytest -q tests/test_cmts_inventory_discovery.py tests/test_sgw_pollers.py tests/test_sgw_endpoints.py

Results / Notes
- 18 passed in 2.45s
- CM registration status and channel set ids now populate when CMTS reports them
