# CLI Service Launcher

Use the `pypnm-cmts serve` command to start the FastAPI service with development-friendly options.

## Table Of Contents

- [Assumptions](#assumptions)
- [When to Use](#when-to-use)
- [Usage](#usage)
- [Discovery (CMTS Inventory)](#discovery-cmts-inventory)
- [Orchestrator Run Modes](#orchestrator-run-modes)
- [Worker Result Persistence](#worker-result-persistence)
- [Coordination Flags](#coordination-flags)
- [Serve Options](#serve-options)
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

```bash
pypnm-cmts discover --cmts-hostname 192.168.0.100 --community public --state-dir ./.data/coordination
```

## Orchestrator Run Modes

Run a single coordination tick and print JSON output.

Worker mode supports a numeric service group id (bound worker) or no `--sg-id` (unbound worker).

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
```

## Next Steps

- Review the system configuration defaults in `src/pypnm_cmts/settings/system.json`.
- Check the FastAPI reference for available endpoints.
