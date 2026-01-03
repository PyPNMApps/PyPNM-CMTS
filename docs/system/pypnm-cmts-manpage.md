# PyPNM-CMTS CLI Man Page

## Name

`pypnm-cmts` - Orchestration, discovery, and service launcher for PyPNM-CMTS.

## Synopsis

```
pypnm-cmts [-h] [-v] {run,run-forever,discover,serve} ...
```

## Description

`pypnm-cmts` controls orchestration ticks, CMTS discovery, and the FastAPI service.
Configuration is sourced from `system.json` unless overridden by CLI flags.

## Commands

### run

Run a single orchestration tick and print JSON output.

```
pypnm-cmts run --mode <standalone|controller|worker|combined> [options]
```

### run-forever

Run orchestration ticks continuously and print JSON output per tick (JSONL).

```
pypnm-cmts run-forever --mode <standalone|controller|worker|combined> [options]
```

### discover

Discover service groups and registered cable modems from a CMTS and print the snapshot.

```
pypnm-cmts discover --cmts-hostname 192.168.0.100 [options]
```

### serve

Start the FastAPI service via Uvicorn.

```
pypnm-cmts serve [options]
```

## Common Orchestrator Options (run, run-forever)

- `--mode`: Execution mode: `standalone` (coordination only), `controller` (leader only), `worker` (lease + tests), `combined` (controller + worker).
- `--config`: Path to `system.json` (defaults to built-in config).
- `--cmts-hostname`: Override `adapter.hostname` for discovery/runtime.
- `--read-community`: Override `adapter.community` (SNMPv2c read community).
- `--write-community`: Override `adapter.write_community` (SNMPv2c write community).
- `--snmp-port`: Override `adapter.port` (SNMP port). `--cmts-port` is deprecated.
- `--sg-id`: Service group id for worker mode (required for bound workers).
- `--owner-id`: Override coordination owner id.
- `--target-service-groups`: Override target SG count per replica (0 means all).
- `--shard-mode`: Shard strategy: `sequential` (default) or `score`.
- `--tick-interval-seconds`: Override tick interval (seconds).
- `--leader-ttl-seconds`: Override leader TTL (seconds).
- `--lease-ttl-seconds`: Override service group lease TTL (seconds).
- `--state-dir`: Override coordination state directory.
- `--election-name`: Override leader election namespace.

## run-forever Options

- `--max-ticks`: Stop after N ticks (optional; useful for tests).

## discover Options

- `--cmts-hostname`: CMTS hostname or IP address (required if not in config).
- `--read-community`: SNMPv2c read community string (default: `public`).
- `--write-community`: SNMPv2c write community string (defaults to read community when empty).
- `--port`: SNMP port for discovery (default: `161`).
- `--config`: Path to `system.json` (defaults to built-in config).
- `--state-dir`: Override coordination state directory for snapshot persistence.
- `--text`: Emit text output instead of JSON.

## serve Options

- `--host`: Host to bind (default: `127.0.0.1`).
- `--port`: Port to bind (default: `8000`).
- `--ssl`: Enable HTTPS (requires cert and key).
- `--cert`: Path to SSL certificate (PEM).
- `--key`: Path to SSL private key (PEM).
- `--cmts-hostname`: Override `adapter.hostname` for SGW startup discovery.
- `--read-community`: Override `adapter.community` for SGW startup discovery.
- `--write-community`: Override `adapter.write_community` for SGW startup discovery.
- `--with-runner`: Start the orchestrator runner in-process (combined mode).
- `--log-level`: Uvicorn log level (default: `info`).
- `--workers`: Number of Uvicorn worker processes (default: `1`).
- `--no-access-log`: Disable Uvicorn access logging.
- `--reload`: Enable auto-reload on file changes (development only).
- `--reload-dir`: Directory to watch for changes (repeatable).
- `--reload-include`: Glob pattern(s) to include for reload (repeatable).
- `--reload-exclude`: Glob pattern(s) to exclude from reload (repeatable).

## Examples

```
pypnm-cmts run --mode standalone
pypnm-cmts run --mode worker --sg-id 1
pypnm-cmts run-forever --mode standalone --tick-interval-seconds 1 --max-ticks 5
pypnm-cmts discover --cmts-hostname 192.168.0.100 --read-community public
pypnm-cmts serve --host 0.0.0.0 --port 8080
pypnm-cmts serve --reload
```

## Configuration Notes

- `serve` uses `system.json` for CMTS hostname and community settings; `--cmts-hostname`, `--read-community`, and `--write-community` can override them for startup discovery.
- For MAC or IP examples in docs, use `aa:bb:cc:dd:ee:ff` and `192.168.0.100`.

## Exit Codes

- `0`: Success.
- `1`: Runtime failure.
- `2`: Usage error or validation failure.
