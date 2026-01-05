# Phase 8 · Step 7d

## Goal
Expose SGW worker identifiers in startup and refresh logs for tracking.

## Summary of changes
- Added SGW worker ID formatting and included worker_id in refresh log extras.
- Logged SGW worker IDs alongside discovered service groups during startup.

## Files changed
- src/pypnm_cmts/sgw/manager.py
- src/pypnm_cmts/sgw/startup.py

## Tests run
- /home/dev01/Projects/PyPNM-CMTS/.env/bin/python -m py_compile src/pypnm_cmts/sgw/manager.py src/pypnm_cmts/sgw/startup.py

## Results / Notes
- Worker IDs are formatted as sgw-<sg_id> and logged for each refresh and startup discovery.
