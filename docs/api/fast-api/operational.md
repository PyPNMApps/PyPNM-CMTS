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
  "timestamp": "2025-01-01T00:00:00+00:00",
  "meta": {
    "mode": "controller",
    "election_name": "cmts-primary",
    "state_dir": ".data/coordination",
    "sg_id": null
  }
}
```
