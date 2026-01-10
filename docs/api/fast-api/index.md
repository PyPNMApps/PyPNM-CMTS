<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Maurice Garcia -->

# FastAPI Reference

FastAPI Endpoint Documentation For PyPNM-CMTS Lives Here.

## Running The Service

Start the FastAPI service using the CLI:

```bash
pypnm-cmts serve --host 127.0.0.1 --port 8000
```

Example health checks:

```bash
curl http://127.0.0.1:8000/ops/health
curl http://127.0.0.1:8000/ops/ready
```

PyPNM endpoints from `pypnm-docsis` are mounted under the `/cm` prefix. Example:

```bash
curl http://127.0.0.1:8000/cm/health
```

CMTS endpoints document JSON-only responses; binary or archive responses are advertised only for PyPNM endpoints that return files.

SGW refresh runs in a background loop after startup prime. Cache-first endpoints
may request a refresh, but they do not execute SNMP in the request thread.

## Current Endpoints

- `GET /cmts/system/sysDescr` - CMTS sysDescr lookup.
- `GET /cmts/servingGroup/get/ids` - SG cache summary and discovered IDs.
- `GET /cmts/servingGroup/status` - SGW startup status and cache readiness.
- `POST /cmts/servingGroup/get/cableModems` - SG cache modem membership (paginated).
- `POST /cmts/servingGroup/get/topology` - SG cache topology summary.
- `POST /cmts/pnm/rxmer/sg/startCapture` - Start serving group RxMER operation.
- `POST /cmts/pnm/rxmer/sg/status` - Get serving group RxMER operation status.
- `POST /cmts/pnm/rxmer/sg/results` - Get serving group RxMER operation results.
- `POST /cmts/pnm/rxmer/sg/cancel` - Cancel serving group RxMER operation.
- `GET /ops/health` - Liveness probe.
- `GET /ops/ready` - Readiness probe.
- `GET /ops/version` - Service identity and version.
- `GET /ops/status` - Operational process status snapshot.
- `GET /ops/servingGroupWorker/process` - SGW worker uptime snapshot.
- `GET /ops/servingGroupWorker/poll-interval` - SGW poll interval summary.
- `POST /ops/servingGroupWorker/restart` - Queue a heavy refresh for an SGW worker.
- `POST /ops/servingGroupWorker/resetCounters` - Reset refresh counters for an SGW worker.

## Endpoint Documentation

- [Operational endpoints](operational.md)
- [RxMER orchestration](pnm-rxmer.md)
- [Serving group endpoints](serving-group.md)

## GET /cmts/system/sysDescr

This endpoint uses runtime CMTS adapter settings from `system.json`.
No request body or query parameters are required.

Example request:

```bash
curl -X GET "http://127.0.0.1:8000/cmts/system/sysDescr"
```


## Next Steps

- Add endpoint summaries as routes are added.
- Link each route section to the owning module under `src/pypnm_cmts/api`.
