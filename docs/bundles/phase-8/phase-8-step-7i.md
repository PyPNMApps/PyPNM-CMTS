# Phase 8 · Step 7i

## Goal
Clarify SGW discovery modes, defaults, and startup logging across related documentation.

## Summary of changes
- Documented SGW discovery modes and defaults in CLI and architecture docs.
- Added startup log markers and discovery mode context to operational and serving-group docs.
- Updated manpage notes to describe discovery mode and adapter overrides.

## Files changed
- docs/system/cli.md
- docs/system/pypnm-cmts-manpage.md
- docs/api/fast-api/operational.md
- docs/api/fast-api/serving-group.md
- docs/architecture/mode-contract.md
- docs/architecture/architecture.md

## Tests run
- None (docs-only)

## Results / Notes
- Documentation now highlights `snmp` as the default discovery mode and explains precheck behavior and log markers.
