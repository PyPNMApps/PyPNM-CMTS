# FastAPI reference

FastAPI endpoint documentation for PyPNM-CMTS will live here.

## Current endpoints

- `POST /system/sysDescr` - CMTS sysDescr lookup.
- `POST /system/serviceGroupTopology` - CMTS service-group topology lookup.
- `GET /ops/health` - Liveness probe.
- `GET /ops/ready` - Readiness probe.
- `GET /ops/version` - Service identity and version.
- `GET /ops/status` - Operational process status snapshot.

## Operational endpoints

- [Operational endpoints](operational.md)

## Next steps

- Add endpoint summaries as routes are added.
- Link each route section to the owning module under `src/pypnm_cmts/api`.
