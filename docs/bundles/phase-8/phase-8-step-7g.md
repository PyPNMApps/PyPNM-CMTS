# Phase 8 · Step 7g

## Goal
Default SGW discovery mode to snmp and update tests/docs to provide adapter configuration explicitly.

## Summary of changes
- Switched the default SGW discovery mode to snmp.
- Updated discovery mode documentation to match the new default.
- Adjusted tests to provide adapter.hostname/community where default snmp validation applies.

## Files changed
- src/pypnm_cmts/config/orchestrator_config.py
- docs/architecture/service-group-workers.md
- tests/test_api_operational.py
- tests/test_orchestrator_runtime_contracts.py
- tests/test_orchestrator_settings.py
- tests/test_serving_group_cache_service.py
- tests/test_sgw_background_refresh.py
- tests/test_sgw_discovery_static.py
- tests/test_sgw_endpoints.py
- tests/test_sgw_manager_metrics_error_duration.py
- tests/test_sgw_manager_refresh.py
- tests/test_sgw_manager_refresh_extra.py
- tests/test_sgw_manager_stop.py
- tests/test_sgw_manager_stop_prestart.py
- tests/test_sgw_observability.py
- tests/test_sgw_readiness.py
- tests/test_sgw_settings.py
- tests/test_sgw_store_aliasing.py
- tests/test_sgw_worker.py

## Tests run
- /home/dev01/Projects/PyPNM-CMTS/.env/bin/python -m py_compile src/pypnm_cmts/config/orchestrator_config.py tests/test_sgw_settings.py tests/test_sgw_manager_stop.py tests/test_sgw_manager_stop_prestart.py tests/test_sgw_endpoints.py tests/test_sgw_store_aliasing.py tests/test_sgw_background_refresh.py tests/test_sgw_observability.py tests/test_sgw_worker.py tests/test_orchestrator_settings.py tests/test_orchestrator_runtime_contracts.py tests/test_api_operational.py tests/test_sgw_readiness.py tests/test_sgw_discovery_static.py tests/test_sgw_manager_metrics_error_duration.py tests/test_sgw_manager_refresh.py tests/test_sgw_manager_refresh_extra.py tests/test_serving_group_cache_service.py
- /home/dev01/Projects/PyPNM-CMTS/.env/bin/python -m pytest -q tests/test_sgw_settings.py tests/test_orchestrator_settings.py tests/test_sgw_endpoints.py tests/test_sgw_background_refresh.py tests/test_sgw_observability.py tests/test_sgw_worker.py tests/test_serving_group_cache_service.py tests/test_sgw_manager_stop.py tests/test_sgw_manager_stop_prestart.py tests/test_sgw_store_aliasing.py tests/test_sgw_manager_metrics_error_duration.py tests/test_sgw_manager_refresh.py tests/test_sgw_manager_refresh_extra.py tests/test_sgw_readiness.py tests/test_api_operational.py tests/test_orchestrator_runtime_contracts.py tests/test_sgw_discovery_static.py

## Results / Notes
- Default discovery mode is now snmp; tests provide adapter configuration explicitly.
