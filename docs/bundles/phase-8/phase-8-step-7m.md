# Phase 8 · Step 7m

Goal
Ensure serving_group.id defaults to an empty list in the canonical CMTS request schema so OpenAPI reflects "all SGs" without a placeholder value.

Summary of changes
- Added an explicit empty-list example for serving_group.id in the canonical request model
- Updated SPDX header year for the modified schema file

Files changed
- src/pypnm_cmts/api/common/cmts_request.py

Tests run
- None (schema-only change)

Results / Notes
- OpenAPI examples should now show serving_group.id as [] by default
