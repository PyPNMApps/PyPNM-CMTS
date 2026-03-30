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
- `sgw.guard` - Shared worker restart policy for SGW supervision.

## Service launcher

- [CLI service launcher](cli.md)
- [CLI option reference](cli-options.md)

PyPNM-CMTS `serve` now reuses the `pypnm-docsis` worker-profile policy for
default worker count and `limit-max-requests`. For the shared hardware sizing
guidance, see:

- [PyPNM Worker Sizing](https://github.com/PyPNMApps/PyPNM/blob/main/docs/system/worker-sizing.md)

## PyPNM-CMTS config menu

Use `pypnm-cmts config-menu` to edit the active `system.json` for CMTS settings,
including SNMP v2c community, TFTP defaults, and PNM file retrieval mode.
CMTS hostname and CMTS SNMP edits also update `CmtsOrchestrator.adapter` values used at startup.
The menu can also reach into the PyPNM (pypnm-docsis) configuration sections within `system.json`
so shared SNMP, TFTP, and retrieval settings stay aligned with CMTS operations.
Menu options:

- CM Config-Menu (launches the PyPNM system config menu).
- CMTS Config-Menu.
- Print current system.json.

The PNM file retrieval option delegates to the PyPNM configurator when
available and walks you through method-specific settings (local, tftp,
or sftp). If the PyPNM tool is not found, the CMTS menu falls back to
editing the retrieval method and its parameters directly.

## Non-interactive config commands

- [Config workflow](config.md)

## PyPNM configuration menu

- Use `pypnm-config-menu` to edit the installed pypnm-docsis `system.json`.
