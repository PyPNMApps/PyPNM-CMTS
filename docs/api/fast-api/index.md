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

## Current Endpoints

- `POST /system/sysDescr` - CMTS sysDescr lookup.
- `POST /system/serviceGroupTopology` - CMTS service-group topology lookup.
- `POST /cmts/servingGroup/get/ids` - SG cache summary and discovered IDs.
- `POST /cmts/servingGroup/get/cableModems` - SG cache modem membership (paginated).
- `POST /cmts/servingGroup/get/topology` - SG cache topology summary.
- `GET /ops/health` - Liveness probe.
- `GET /ops/ready` - Readiness probe.
- `GET /ops/version` - Service identity and version.
- `GET /ops/status` - Operational process status snapshot.

## Endpoint Documentation

- [Operational endpoints](operational.md)
- [Serving group endpoints](serving-group.md)

## Next Steps

- Add endpoint summaries as routes are added.
- Link each route section to the owning module under `src/pypnm_cmts/api`.
