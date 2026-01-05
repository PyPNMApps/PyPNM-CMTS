# Phase 8 · Step 7e

## Goal
Include SGWorkerID in SGW startup and refresh logs so pypnm.log shows the worker identifier.

## Summary of changes
- Added SGWorkerID label to SGW refresh log messages.
- Labeled startup worker ID list with SGWorkerID in logs.

## Files changed
- src/pypnm_cmts/sgw/manager.py
- src/pypnm_cmts/sgw/startup.py

## Tests run
- /home/dev01/Projects/PyPNM-CMTS/.env/bin/python -m py_compile src/pypnm_cmts/sgw/manager.py src/pypnm_cmts/sgw/startup.py

## Results / Notes
- SGWorkerID now appears in log messages even when the log formatter ignores extra fields.
