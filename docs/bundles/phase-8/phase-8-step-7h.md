# Phase 8 · Step 7h

## Goal
Prevent duplicate log handlers so startup logs are not emitted twice.

## Summary of changes
- Added a logging configuration guard to avoid reconfiguring the root logger when startup runs multiple times.

## Files changed
- src/pypnm_cmts/startup/startup.py

## Tests run
- /home/dev01/Projects/PyPNM-CMTS/.env/bin/python -m py_compile src/pypnm_cmts/startup/startup.py

## Results / Notes
- Startup logging now short-circuits when handlers already exist.
