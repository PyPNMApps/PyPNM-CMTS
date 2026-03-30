<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Maurice Garcia -->

# FastAPI Reference

FastAPI Endpoint Documentation For PyPNM-CMTS Lives Here.

## Navigation By Intent

- Operational health and runtime state:
  - [Operational endpoints](operational.md)
- Serving-group data and modem actions:
  - [Serving group endpoints](serving-group.md)
- PNM capture orchestration by serving group:
  - [SG PNM operations](pnm-sg-operations.md)
  - [RxMER deep dive](pnm-rxmer.md)
  - [SG operations data model](pypnm-cmts/sg-operations.md)

## Endpoint Family Map

- `GET /ops/*`:
  - Liveness/readiness/version and process visibility.
- `GET|POST /cmts/servingGroup/*`:
  - Service-group inventory, topology, and modem-scope operations.
- `POST /cmts/pnm/sg/*`:
  - `startCapture`, `status`, `results`, `cancel` orchestration workflow.

## Running The Service

Start the FastAPI service using the CLI:

```bash
pypnm-cmts serve --host 127.0.0.1 --port 8080
```

By default, `pypnm-cmts serve` now reuses the same worker-profile selection
logic as `pypnm-docsis`:

- seeded worker profile when available
- otherwise CPU/RAM auto-detection

The two intentional exceptions are:

- `--reload` forces `workers=1`
- `--with-runner` forces `workers=1`
- `sgw.enabled=true` forces `workers=1`

For the shared sizing policy and hardware scenarios, see:

- [PyPNM Worker Sizing](https://github.com/PyPNMApps/PyPNM/blob/main/docs/system/worker-sizing.md)

Example health checks:

```bash
curl http://127.0.0.1:8080/ops/health
curl http://127.0.0.1:8080/ops/ready
```

PyPNM endpoints from `pypnm-docsis` are mounted under the `/cm` prefix by default. Example:

```bash
curl http://127.0.0.1:8080/cm/health
```

To suppress those legacy PyPNM endpoints at startup, run:

```bash
pypnm-cmts serve --mute-pypnm-endpoints
```

Equivalent environment override:

```bash
export PYPNM_CMTS_MUTE_PYPNM_ENDPOINTS=1
```

To mute routes by FastAPI tag:

```bash
pypnm-cmts serve --mute-tags "Orchestrator,Operational"
```

Hard policy mode returns `403 Forbidden` for matched tags:

```bash
pypnm-cmts serve --mute-tags "Orchestrator,Operational" --mute-tags-hard
```

CMTS endpoints document JSON-only responses; binary or archive responses are advertised only for PyPNM endpoints that return files.

SGW refresh runs in a background loop after startup discovery. Cache-first endpoints
may request a refresh, but they do not execute SNMP in the request thread.

## Current Endpoints

- `GET /cmts/system/sysDescr` - CMTS sysDescr lookup.
- `POST /cmts/system/webService/reload` - Write the configured reload sentinel for an external watcher.
- `GET /cmts/servingGroup/operations/get/ids` - SG cache summary and discovered IDs.
- `GET /cmts/servingGroup/operations/get/status` - SGW startup status and cache readiness.
- `POST /cmts/servingGroup/operations/get/cableModems` - SG cache modem membership (paginated).
- `POST /cmts/servingGroup/operations/get/topology` - SG cache topology summary.
- `POST /cmts/servingGroup/cableModem/operations/docsDevResetNow` - Issue docsDevResetNow for scoped cable modems.
- `POST /cmts/servingGroup/cableModem/operations/getSysDescr` - Collect per-SG cable modem sysDescr payloads.
- `POST /cmts/pnm/sg/ds/ofdm/rxmer/startCapture` - Start serving group RxMER operation.
- `POST /cmts/pnm/sg/ds/ofdm/rxmer/status` - Get serving group RxMER operation status.
- `POST /cmts/pnm/sg/ds/ofdm/rxmer/results` - Get serving group RxMER operation results.
- `POST /cmts/pnm/sg/ds/ofdm/rxmer/cancel` - Cancel serving group RxMER operation.
- `POST /cmts/pnm/sg/ds/histogram/startCapture` - Start serving group downstream Histogram operation.
- `POST /cmts/pnm/sg/ds/histogram/status` - Get serving group downstream Histogram operation status.
- `POST /cmts/pnm/sg/ds/histogram/results` - Get serving group downstream Histogram operation results.
- `POST /cmts/pnm/sg/ds/histogram/cancel` - Cancel serving group downstream Histogram operation.
- `POST /cmts/pnm/sg/ds/ofdm/channelEstCoeff/startCapture` - Start serving group ChannelEstCoeff operation.
- `POST /cmts/pnm/sg/ds/ofdm/channelEstCoeff/status` - Get serving group ChannelEstCoeff operation status.
- `POST /cmts/pnm/sg/ds/ofdm/channelEstCoeff/results` - Get serving group ChannelEstCoeff operation results.
- `POST /cmts/pnm/sg/ds/ofdm/channelEstCoeff/cancel` - Cancel serving group ChannelEstCoeff operation.
- `POST /cmts/pnm/sg/ds/ofdm/fecSummary/startCapture` - Start serving group FecSummary operation.
- `POST /cmts/pnm/sg/ds/ofdm/fecSummary/status` - Get serving group FecSummary operation status.
- `POST /cmts/pnm/sg/ds/ofdm/fecSummary/results` - Get serving group FecSummary operation results.
- `POST /cmts/pnm/sg/ds/ofdm/fecSummary/cancel` - Cancel serving group FecSummary operation.
  - See [FecSummary orchestration deep dive](pnm-fec-summary.md).
- `POST /cmts/pnm/sg/ds/ofdm/constellationDisplay/startCapture` - Start serving group ConstellationDisplay operation.
- `POST /cmts/pnm/sg/ds/ofdm/constellationDisplay/status` - Get serving group ConstellationDisplay operation status.
- `POST /cmts/pnm/sg/ds/ofdm/constellationDisplay/results` - Get serving group ConstellationDisplay operation results.
- `POST /cmts/pnm/sg/ds/ofdm/constellationDisplay/cancel` - Cancel serving group ConstellationDisplay operation.
  - See [ConstellationDisplay orchestration deep dive](pnm-constellation-display.md).
- `POST /cmts/pnm/sg/ds/ofdm/modulationProfile/startCapture` - Start serving group ModulationProfile operation.
- `POST /cmts/pnm/sg/ds/ofdm/modulationProfile/status` - Get serving group ModulationProfile operation status.
- `POST /cmts/pnm/sg/ds/ofdm/modulationProfile/results` - Get serving group ModulationProfile operation results.
- `POST /cmts/pnm/sg/ds/ofdm/modulationProfile/cancel` - Cancel serving group ModulationProfile operation.
  - See [ModulationProfile orchestration deep dive](pnm-modulation-profile.md).
- `POST /cmts/pnm/sg/spectrumAnalyzer/startCapture` - Start serving group full bandwidth SpectrumAnalyzer operation.
- `POST /cmts/pnm/sg/spectrumAnalyzer/status` - Get serving group full bandwidth SpectrumAnalyzer operation status.
- `POST /cmts/pnm/sg/spectrumAnalyzer/results` - Get serving group full bandwidth SpectrumAnalyzer operation results.
- `POST /cmts/pnm/sg/spectrumAnalyzer/cancel` - Cancel serving group full bandwidth SpectrumAnalyzer operation.
- `POST /cmts/pnm/sg/ds/ofdm/spectrumAnalyzer/startCapture` - Start serving group downstream OFDM SpectrumAnalyzer operation.
- `POST /cmts/pnm/sg/ds/ofdm/spectrumAnalyzer/status` - Get serving group downstream OFDM SpectrumAnalyzer operation status.
- `POST /cmts/pnm/sg/ds/ofdm/spectrumAnalyzer/results` - Get serving group downstream OFDM SpectrumAnalyzer operation results.
- `POST /cmts/pnm/sg/ds/ofdm/spectrumAnalyzer/cancel` - Cancel serving group downstream OFDM SpectrumAnalyzer operation.
- `POST /cmts/pnm/sg/ds/scqam/spectrumAnalyzer/startCapture` - Start serving group downstream SCQAM SpectrumAnalyzer operation.
- `POST /cmts/pnm/sg/ds/scqam/spectrumAnalyzer/status` - Get serving group downstream SCQAM SpectrumAnalyzer operation status.
- `POST /cmts/pnm/sg/ds/scqam/spectrumAnalyzer/results` - Get serving group downstream SCQAM SpectrumAnalyzer operation results.
- `POST /cmts/pnm/sg/ds/scqam/spectrumAnalyzer/cancel` - Cancel serving group downstream SCQAM SpectrumAnalyzer operation.
- `POST /cmts/pnm/sg/us/ofdma/preEqualization/startCapture` - Start serving group PreEqualization operation.
- `POST /cmts/pnm/sg/us/ofdma/preEqualization/status` - Get serving group PreEqualization operation status.
- `POST /cmts/pnm/sg/us/ofdma/preEqualization/results` - Get serving group PreEqualization operation results.
- `POST /cmts/pnm/sg/us/ofdma/preEqualization/cancel` - Cancel serving group PreEqualization operation.
- `GET /ops/health` - Liveness probe.
- `GET /ops/health/memoryDetail` - Lightweight process, SGW cache, runner, thread, and Python object-family memory-debug counters.
- `GET /ops/ready` - Readiness probe.
- `GET /ops/version` - Service identity and version.
- `GET /ops/status` - Operational process status snapshot.
- `GET /ops/servingGroupWorker/process` - SGW worker uptime snapshot.
- `GET /ops/servingGroupWorker/poll-interval` - SGW poll interval summary.
- `POST /ops/servingGroupWorker/restart` - Queue a heavy refresh for an SGW worker.
- `POST /ops/servingGroupWorker/resetCounters` - Reset refresh counters for an SGW worker.

## Endpoint Documentation

- [Operational endpoints](operational.md)
- [Serving group endpoints](serving-group.md)
- [SG PNM operations](pnm-sg-operations.md)
- [RxMER deep dive](pnm-rxmer.md)
- [SG operations data model](pypnm-cmts/sg-operations.md)

## GET /cmts/system/sysDescr

This endpoint uses runtime CMTS adapter settings from `system.json`.
No request body or query parameters are required.

Example request:

```bash
curl -X GET "http://127.0.0.1:8080/cmts/system/sysDescr"
```

## POST /cmts/system/webService/reload

This endpoint is production-safe because it does not try to self-restart the process.
It writes a configured sentinel file that an external watcher or supervisor should
observe and use to restart the web service.

Example request:

```bash
curl -X POST "http://127.0.0.1:8080/cmts/system/webService/reload"
```

Example watcher:

```bash
./tools/support/watch_reload_sentinel.py \
  --sentinel /run/pypnm-cmts/webservice.reload \
  --restart-cmd "systemctl restart pypnm-cmts"
```


## Next Steps

- Add endpoint summaries as routes are added.
- Link each route section to the owning module under `src/pypnm_cmts/api`.
