# Phase 8 · Step 7f

## Goal
Log SGW discovery mode at startup and document SGW discovery modes and logging.

## Summary of changes
- Added SGW discovery mode logging to startup.
- Documented static vs SNMP discovery, defaults, and startup logging.

## Files changed
- src/pypnm_cmts/sgw/startup.py
- docs/architecture/service-group-workers.md

## Tests run
- None (docs and logging change only)

## Results / Notes
- Startup now logs the active discovery mode before precheck and discovery.
