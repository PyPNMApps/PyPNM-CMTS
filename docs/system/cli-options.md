# PyPNM-CMTS CLI Option Reference

Complete option index for `pypnm-cmts`.

## Global

- `-h`, `--help` Show help.
- `-v`, `--version` Show version.

## Commands

- `run`
- `run-forever`
- `discover`
- `serve`
- `config`
- `config-menu`

## run

Usage:

```bash
pypnm-cmts run --mode <standalone|controller|worker|combined> [options]
```

Options:

- `--mode` Required orchestrator mode.
- `--config` Optional `system.json` path.
- `--cmts-hostname` Override adapter hostname.
- `--read-community` Override adapter SNMP read community.
- `--write-community` Override adapter SNMP write community.
- `--snmp-port` Override adapter SNMP port.
- `--cmts-port` Deprecated alias for `--snmp-port`.
- `--sg-id` Worker service group id.
- `--owner-id` Override coordination owner id.
- `--target-service-groups` Override SG target count per replica (0 means all).
- `--shard-mode` Shard mode: `sequential` or `score`.
- `--tick-interval-seconds` Tick interval override.
- `--leader-ttl-seconds` Leader TTL override.
- `--lease-ttl-seconds` Lease TTL override.
- `--state-dir` Coordination state directory override.
- `--election-name` Election namespace override.
- `--cm-snmpv2c-write-community` Override CM request default.
- `--cm-tftp-ipv4` Override CM request default.
- `--cm-tftp-ipv6` Override CM request default.

## run-forever

Usage:

```bash
pypnm-cmts run-forever --mode <standalone|controller|worker|combined> [options]
```

Options:

- All `run` options.
- `--max-ticks` Stop after N ticks.

## discover

Usage:

```bash
pypnm-cmts discover [options]
```

Options:

- `--cmts-hostname` CMTS hostname or IP.
- `--read-community` SNMP read community.
- `--write-community` SNMP write community.
- `--port` Discovery SNMP port (default `161`).
- `--config` Optional `system.json` path.
- `--state-dir` Snapshot persistence directory.
- `--text` Emit text output instead of JSON.

## serve

Usage:

```bash
pypnm-cmts serve [options]
```

Options:

- `--host` Bind host (default `127.0.0.1`).
- `--port` Bind port (default `8000`).
- `--ssl` Enable HTTPS.
- `--cert` TLS certificate path.
- `--key` TLS private key path.
- `--cmts-hostname` Override adapter hostname for SGW startup.
- `--read-community` Override adapter read community for SGW startup.
- `--write-community` Override adapter write community for SGW startup.
- `--cm-snmpv2c-write-community` Override CM request default.
- `--cm-tftp-ipv4` Override CM request default.
- `--cm-tftp-ipv6` Override CM request default.
- `--with-runner` Enable in-process combined mode runner.
- `--mute-pypnm-endpoints` Suppress legacy PyPNM endpoints under `/cm`.
- `--log-level` Uvicorn log level.
- `--workers` Uvicorn worker count.
- `--no-access-log` Disable access log.
- `--reload` Enable autoreload.
- `--reload-dir` Autoreload watch directory (repeatable).
- `--reload-include` Autoreload include glob (repeatable).
- `--reload-exclude` Autoreload exclude glob (repeatable).

Environment equivalent for endpoint muting:

- `PYPNM_CMTS_MUTE_PYPNM_ENDPOINTS=1`

## config-menu

Usage:

```bash
pypnm-cmts config-menu [options]
```

Options:

- `--config` Optional `system.json` path.

## config

Usage:

```bash
pypnm-cmts config <init|validate|show> [options]
```

### config init

- `--path` Target `system.json` path.
- `--force` Overwrite existing file.
- `--print` Print generated config.
- `--dry-run` Do not write file.

### config validate

- `--path` Optional `system.json` path.
- `--json` Emit JSON output.

### config show

- `--path` Optional `system.json` path.
- `--pretty` Pretty-print JSON output.
