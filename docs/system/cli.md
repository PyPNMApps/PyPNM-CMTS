# CLI Service Launcher

Use the `pypnm-cmts serve` command to start the FastAPI service with development-friendly options.

## Table Of Contents

- [Assumptions](#assumptions)
- [When to Use](#when-to-use)
- [Usage](#usage)
- [Discovery (CMTS Inventory)](#discovery-cmts-inventory)
- [SGW Startup Discovery Modes](#sgw-startup-discovery-modes)
- [Orchestrator Run Modes](#orchestrator-run-modes)
- [Worker Result Persistence](#worker-result-persistence)
- [Coordination Flags](#coordination-flags)
- [Serve Options](#serve-options)
- [Security Tools](#security-tools)
- [Next Steps](#next-steps)

## Assumptions

- Commands are run from the repository root.
- Virtual environment activation is handled by your environment.

## When to Use

- Start the CMTS API locally during development.
- Enable hot reload when iterating on API code.

## Usage

### Basic HTTP

```bash
pypnm-cmts serve
```

The service binds to `127.0.0.1:8000` by default and reads CMTS adapter
settings from `system.json`. Use `pypnm-cmts config-menu` to set the CMTS
hostname and SNMP communities, or pass `--cmts-hostname` and `--read-community`
as overrides.

To suppress legacy PyPNM endpoints mounted under `/cm`:

```bash
pypnm-cmts serve --mute-pypnm-endpoints
```

### Custom host/port

```bash
pypnm-cmts serve --host 0.0.0.0 --port 8080
```

### Reload on changes

```bash
pypnm-cmts serve --reload
```

### Reload with custom watch paths

```bash
pypnm-cmts serve --reload --reload-dir src --reload-dir tools
```

### HTTPS

```bash
pypnm-cmts serve --ssl --cert ./certs/cert.pem --key ./certs/key.pem
```

## Discovery (CMTS Inventory)

Discover service groups and registered cable modems from a CMTS using SNMP.
If `--write-community` is omitted or empty, the discovery path uses the effective read community.
Use `--port` to override the SNMP port for the `discover` command; `run` and `serve` use `--snmp-port`.
The `run` and `run-forever` commands load CMTS adapter settings from system.json unless you pass adapter overrides.

```bash
pypnm-cmts discover --cmts-hostname 192.168.0.100 --read-community public --state-dir ./.data/coordination
```

```bash
pypnm-cmts discover --cmts-hostname 192.168.0.100 --read-community public --write-community private --state-dir ./.data/coordination
```

## SGW Startup Discovery Modes

SGW discovery runs during `pypnm-cmts serve` startup. The mode is configured in `CmtsOrchestrator.sgw.discovery.mode`.
If the mode is missing or empty, the default is `snmp`.

### SNMP Mode (Default)

SNMP discovery queries the CMTS to enumerate SG IDs.

- Uses adapter settings from system.json or CLI/env overrides:
  - `adapter.hostname`
  - `adapter.community`
  - `adapter.port`
- Runs a precheck before discovery:
  - ICMP ping
  - SNMP sysDescr

Example: set discovery mode in system.json and override the target at runtime:

```json
{
  "CmtsOrchestrator": {
    "sgw": {
      "enabled": true,
      "discovery": {
        "mode": "snmp"
      }
    }
  }
}
```

```bash
pypnm-cmts serve --cmts-hostname 192.168.0.100 --read-community public --write-community public
```

### Static Mode

Static discovery uses the configured service group list and performs no SNMP calls.

- Requires `service_groups` entries to be present.
- If the list is empty, discovery returns no SGs.

```json
{
  "CmtsOrchestrator": {
    "sgw": {
      "enabled": true,
      "discovery": {
        "mode": "static"
      }
    },
    "service_groups": [
      {
        "sg_id": 1,
        "enabled": true
      },
      {
        "sg_id": 2,
        "enabled": true
      }
    ]
  }
}
```

## Orchestrator Run Modes

Run a single coordination tick and print JSON output.

Worker mode supports a numeric service group id (bound worker) or no `--sg-id` (unbound worker).
Use adapter overrides to supply CMTS hostname and read/write communities at runtime without editing system.json.

Tick index is 1-based. The one-shot run reports `tick_index` = 1.
Continuous runs increment `tick_index` once per tick in the same process.
Worker persistence happens only when `lease_held` is true.

```bash
pypnm-cmts run --mode standalone
```

```bash
pypnm-cmts run --mode controller
```

```bash
pypnm-cmts run --mode worker --sg-id 1
```

Run continuously with a tick interval (seconds):

```bash
pypnm-cmts run-forever --mode standalone --tick-interval-seconds 1 --max-ticks 5
```

```bash
pypnm-cmts run-forever --mode controller --tick-interval-seconds 1
```

```bash
pypnm-cmts run-forever --mode worker --sg-id 1 --tick-interval-seconds 1
```

```bash
pypnm-cmts run-forever --mode worker --tick-interval-seconds 1
```

## Worker Result Persistence

Worker mode persists test results under the coordination state directory:

```
<state_dir>/results/sg_<sg_id>/
```

Each file name is deterministic per tick:

```
sg<sg_id>_tick<tick_index>_<test_name>.json
```

Tick indices are 1-based within a single run.

## Coordination Flags

These flags are supported by `run` and `run-forever`.

Example:

```bash
pypnm-cmts run-forever --mode standalone --owner-id replica-1 --target-service-groups 2 --shard-mode score \
  --cmts-hostname 192.168.0.100 --read-community public --snmp-port 161 \
  --state-dir ./.data/coordination --election-name cmts-primary
```

Flags:
- --owner-id <str>
- --target-service-groups <int>
- --shard-mode sequential|score
- --tick-interval-seconds <float>
- --leader-ttl-seconds <int>
- --lease-ttl-seconds <int>
- --state-dir <path>
- --election-name <str>
- --cmts-hostname <str>
- --read-community <str>
- --write-community <str>
- --snmp-port <int> (SNMP port override; --cmts-port is deprecated)

If both `--snmp-port` and `--cmts-port` are supplied, `--snmp-port` takes precedence and the deprecated alias emits a warning.

## Serve Options

These options apply to `pypnm-cmts serve`.

```text
-v, --version Show PyPNM-CMTS version and exit.
--host Host to bind (default: 127.0.0.1)
--port Port to bind (default: 8000)
--ssl Enable HTTPS (requires cert and key)
--cert Path to SSL certificate (default: ./certs/cert.pem)
--key Path to SSL private key (default: ./certs/key.pem)
--log-level Uvicorn log level (default: info)
--workers Number of worker processes (default: 1)
--no-access-log Disable Uvicorn access log
--reload Enable auto-reload on file changes (dev only)
--reload-dir Directory to watch for changes (repeatable)
--reload-include Glob pattern(s) to include (repeatable; default: *.py)
--reload-exclude Glob pattern(s) to exclude (repeatable)
--mute-pypnm-endpoints Suppress legacy PyPNM routes under /cm at startup
```

For full command and option coverage across all CLI commands, see [CLI option reference](cli-options.md).

## Security Tools

Repository security checks live under `tools/security`.
The MAC scan respects `.gitignore` directory entries by default; use `--skip-gitignore` to scan ignored paths.

```bash
./tools/security/scan-mac-addresses.py --fail-on-found
```

```bash
./tools/security/scan-mac-addresses.py --fail-on-found --skip-gitignore
```

## Next Steps

- Review the system configuration defaults in `src/pypnm_cmts/settings/system.json`.
- Check the FastAPI reference for available endpoints.
