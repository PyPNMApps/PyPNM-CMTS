# System configuration

System configuration references for PyPNM-CMTS.

On startup, PyPNM-CMTS ensures the CMTS template block exists in the installed `pypnm-docsis` `system.json`.

## CmtsOrchestrator settings

`CmtsOrchestrator` defines orchestration boundaries and defaults without executing any orchestration logic.
This section is read by `CmtsOrchestratorSettings` and supports mode selection, adapter targeting,
service group descriptors, and default test names.

Key fields:

- `mode` - Execution mode (`standalone`, `controller`, `worker`).
- `adapter` - CMTS adapter selection (kind, cmts_index, label).
- `service_groups` - Optional list of service group descriptors.
- `default_tests` - Optional list of test names. If missing or empty, defaults to `["ds_ofdm_rxmer"]`.

## Service launcher

- [CLI service launcher](cli.md)

## PyPNM configuration menu

- Use `pypnm-config-menu` to edit the installed pypnm-docsis `system.json`.
