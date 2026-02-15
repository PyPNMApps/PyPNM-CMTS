# Operational Endpoints

Read-Only Operational Endpoints For Health, Readiness, And Version.
All responses include the common `meta` identity block (mode, election_name, state_dir, sg_id).

## Endpoints

### GET /ops/health

Liveness Probe.
Always returns HTTP 200 if the process is running.

Example:

```bash
curl -s http://127.0.0.1:8000/ops/health
```

Response shape:

```json
{
  "status": "ok",
  "timestamp": "2025-01-01T00:00:00+00:00",
  "meta": {
    "mode": "controller",
    "election_name": "cmts-primary",
    "state_dir": ".data/coordination",
    "sg_id": null
  }
}
```

### GET /ops/ready

Readiness Probe.
Returns HTTP 200 when local prerequisites are satisfied, otherwise HTTP 503 with a structured body.

Readiness checks:

- Controller: state_dir exists or can be created, required subdirectories can be created, and state_dir is writable.
- Worker: state_dir exists and is readable, and sg_id is bound.

Example:

```bash
curl -s http://127.0.0.1:8000/ops/ready
```

Response shape (ready):

```json
{
  "status": "ok",
  "failed_check": null,
  "message": "",
  "timestamp": "2025-01-01T00:00:00+00:00",
  "meta": {
    "mode": "controller",
    "election_name": "cmts-primary",
    "state_dir": ".data/coordination",
    "sg_id": null
  }
}
```

Response shape (not ready):

```json
{
  "status": "error",
  "failed_check": "state_dir_access",
  "message": "state_dir is not writable: .data/coordination",
  "timestamp": "2025-01-01T00:00:00+00:00",
  "meta": {
    "mode": "controller",
    "election_name": "cmts-primary",
    "state_dir": ".data/coordination",
    "sg_id": null
  }
}
```

### GET /ops/status

Read-Only Operational Status Snapshot.
Reports controller and worker process visibility and PID record state.

Example:

```bash
curl -s http://127.0.0.1:8000/ops/status
```

Response shape:

```json
{
  "status": "ok",
  "timestamp": "2025-01-01T00:00:00+00:00",
  "meta": {
    "mode": "controller",
    "election_name": "cmts-primary",
    "state_dir": ".data/coordination",
    "sg_id": null
  },
  "controller": {
    "pidfile_path": ".data/coordination/pids/controller.pid",
    "pidfile_exists": true,
    "pid": 12345,
    "is_running": true,
    "sg_id": null
  },
  "workers": [
    {
      "pidfile_path": ".data/coordination/pids/worker_1.pid",
      "pidfile_exists": true,
      "pid": 23456,
      "is_running": true,
      "sg_id": 1
    }
  ],
  "pid_records_missing": false,
  "pid_records_stale": false,
  "fallback_used": false
}
```

Notes:

- pid_records_missing is true when the pids directory is missing or empty.
- pid_records_stale is true when pidfiles exist but none of the recorded PIDs are running.
- fallback_used is true only when fallback discovery finds processes with an exact --election-name match.
- workers are sorted by sg_id ascending, with unbound workers listed last; ties break by pid then pidfile_path.

## SGW Startup And Discovery Logs

FastAPI startup runs SGW discovery and starts background refresh. The startup log sequence clarifies which discovery mode was used
and whether the CMTS precheck succeeded (SNMP mode only).

Expected log markers:

- `SGW discovery mode: snmp`
- `CMTS precheck: hostname=192.168.0.100 inet=192.168.0.100 ping=ok snmp=ok`
- `Discovered SG IDs: [<sg_id>, ...]`
- `SGWorkerID: [sgw-<sg_id>, ...]`

If discovery returns an empty list, readiness is still reported as `ready` but endpoints that depend on SG cache will
return empty results.

## SGW Refresh And SysDescr Logs

Expected refresh start markers:

- `[REFRESH_HEAVY] worker=sgw-<sg_id>`
- `[REFRESH_LIGHT] worker=sgw-<sg_id>`

Heavy refresh modem sysDescr logs include modem context fields:

- `HeavyPoll [CM_SYSDESCR_ATTEMPT] sg_id=... mac=... ip=... community=...`
- `HeavyPoll [CM_SYSDESCR_RESULT] sg_id=... mac=... ip=... community=... outcome=empty|exception|success`

When SNMP timeouts occur overnight, use `sg_id`, `mac`, and `ip` from `HeavyPoll` result logs to identify failing modems.

### GET /ops/servingGroupWorker/process

SGW Worker Process Summary.
Returns worker identifiers with uptime snapshots.

Example:

```bash
curl -s http://127.0.0.1:8000/ops/servingGroupWorker/process
```

Response shape:

```json
{
  "status": "ok",
  "timestamp": "2025-01-01T00:00:00+00:00",
  "meta": {
    "mode": "controller",
    "election_name": "cmts-primary",
    "state_dir": ".data/coordination",
    "sg_id": null
  },
  "workers": [
    {
      "worker_id": "sgw-1",
      "sg_id": 1,
      "started_epoch": 1700000000.0,
      "uptime_seconds": 60.0
    }
  ],
  "message": ""
}
```

### GET /ops/servingGroupWorker/poll-interval

SGW Poll Interval Summary.
Returns poll intervals and refresh counts for each worker.

Example:

```bash
curl -s http://127.0.0.1:8000/ops/servingGroupWorker/poll-interval
```

Response shape:

```json
{
  "status": "ok",
  "timestamp": "2025-01-01T00:00:00+00:00",
  "meta": {
    "mode": "controller",
    "election_name": "cmts-primary",
    "state_dir": ".data/coordination",
    "sg_id": null
  },
  "workers": [
    {
      "worker_id": "sgw-1",
      "sg_id": 1,
      "heavy_interval_seconds": 300,
      "heavy_count": 1,
      "light_interval_seconds": 60,
      "light_count": 1
    }
  ],
  "message": ""
}
```

### POST /ops/servingGroupWorker/restart

Queue a heavy refresh for a specific SGW worker.

Example:

```bash
curl -s -X POST http://127.0.0.1:8000/ops/servingGroupWorker/restart \
  -H "Content-Type: application/json" \
  -d '{"worker_id":"sgw-1"}'
```

Response shape:

```json
{
  "status": "ok",
  "timestamp": "2025-01-01T00:00:00+00:00",
  "meta": {
    "mode": "controller",
    "election_name": "cmts-primary",
    "state_dir": ".data/coordination",
    "sg_id": null
  },
  "sg_id": 1,
  "message": "queued heavy refresh for sgw-1"
}
```

### POST /ops/servingGroupWorker/resetCounters

Reset SGW refresh counters for a specific worker.

Example:

```bash
curl -s -X POST http://127.0.0.1:8000/ops/servingGroupWorker/resetCounters \
  -H "Content-Type: application/json" \
  -d '{"worker_id":"sgw-1"}'
```

Response shape:

```json
{
  "status": "ok",
  "timestamp": "2025-01-01T00:00:00+00:00",
  "meta": {
    "mode": "controller",
    "election_name": "cmts-primary",
    "state_dir": ".data/coordination",
    "sg_id": null
  },
  "sg_id": 1,
  "message": "reset refresh counts for sgw-1"
}
```

### GET /ops/version

Service Identity, Version, And Runtime Metadata.

Example:

```bash
curl -s http://127.0.0.1:8000/ops/version
```

Response shape:

```json
{
  "application": "pypnm-cmts",
  "version": "0.1.0",
  "python_version": "3.10.12",
  "build_metadata": "",
  "timestamp": "2025-01-01T00:00:00+00:00",
  "meta": {
    "mode": "controller",
    "election_name": "cmts-primary",
    "state_dir": ".data/coordination",
    "sg_id": null
  }
}
```

## Live CMTS Tests

Live CMTS tests are skipped by default and must be explicitly enabled. They validate SNMP connectivity for system endpoints.

Required environment variables:

- PYPNM_CMTS_LIVE_HOSTNAME
- PYPNM_CMTS_LIVE_SNMP_COMMUNITY
- PYPNM_CMTS_LIVE_SNMP_PORT (optional, default 161)

Enable and run:

```bash
PYPNM_CMTS_RUN_LIVE=1 \
PYPNM_CMTS_LIVE_HOSTNAME=192.168.0.100 \
PYPNM_CMTS_LIVE_SNMP_COMMUNITY=public \
/home/dev01/Projects/PyPNM-CMTS/.env/bin/python -m pytest -q -m live_cmts tests/live/test_live_system_endpoints.py
```
