# PyPNM-CMTS documentation hub

Use this page to get to the right guide for installs, operations, API references, and examples.
PyPNM-CMTS is designed to service a single CMTS instance; scale by Service Group (SG). Deployments are supported via Docker.

## New to PyPNM-CMTS? (start here)

- [Project overview](architecture/index.md) - what PyPNM-CMTS provides and how to run the CLI.
- [Install flow](install/index.md) - clone, run `./install.sh`, and activate `.env`.
- [CLI examples](examples/cli.md) - quick starts for CMTS sysDescr lookups.

## Configure and operate

- [System configuration](system/index.md) - how system settings and defaults are organized.
- [Operational tools](tools/index.md) - helpers in `tools/`.
- [Scripts](scripts/index.md) - repository scripts and setup helpers.

## Develop and automate

- [API reference](api/index.md) - FastAPI endpoints and Python helpers.
- [Examples](examples/index.md) - runnable workflows.
- [Tests](tests/index.md) - how to run and extend automated tests.

## Find API endpoints quickly

- [Operational endpoints](api/fast-api/operational.md) - health, readiness, process status, and SGW runtime controls.
- [Serving group endpoints](api/fast-api/serving-group.md) - serving-group IDs, modem lists, topology, and cable modem operations.
- [SG PNM operations](api/fast-api/pnm-sg-operations.md) - start, status, results, and cancel flows for SG PNM captures.
- [RxMER endpoint deep dive](api/fast-api/pnm-rxmer.md) - full lifecycle and payload contract for RxMER orchestration.

## Release and support

- [Release notes](release/index.md) - version tracking and changes.
- [Issues and support bundles](issues/index.md) - how to capture diagnostics and report issues.

## Need more context?

- [Style guide](style-guide.md) - documentation writing conventions.
