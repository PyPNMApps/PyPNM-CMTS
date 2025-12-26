# CLI service launcher

Use the `pypnm-cmts` command to start the FastAPI service with development-friendly options.

## When to use

- Start the CMTS API locally during development.
- Enable hot reload when iterating on API code.

## Usage

### Basic HTTP

```bash
pypnm-cmts
```

### Custom host/port

```bash
pypnm-cmts --host 0.0.0.0 --port 8080
```

### Reload on changes

```bash
pypnm-cmts --reload
```

### Reload with custom watch paths

```bash
pypnm-cmts --reload --reload-dir src --reload-dir tools
```

### HTTPS

```bash
pypnm-cmts --ssl --cert ./certs/cert.pem --key ./certs/key.pem
```

## Planned coordination flags

These flags are documented for coordination wiring and are not yet exposed in the CLI.

Example (planned):

```bash
pypnm-cmts run --mode standalone --owner-id replica-1 --target-service-groups 2 --shard-mode score
```

Planned flags:
- --owner-id <str>
- --target-service-groups <int>
- --shard-mode sequential|score

## Options

```text
-v, --version          Show PyPNM-CMTS version and exit.
--host                 Host to bind (default: 127.0.0.1)
--port                 Port to bind (default: 8000)
--ssl                  Enable HTTPS (requires cert and key)
--cert                 Path to SSL certificate (default: ./certs/cert.pem)
--key                  Path to SSL private key (default: ./certs/key.pem)
--log-level            Uvicorn log level (default: info)
--workers              Number of worker processes (default: 1)
--no-access-log        Disable Uvicorn access log
--reload               Enable auto-reload on file changes (dev only)
--reload-dir           Directory to watch for changes (repeatable)
--reload-include        Glob pattern(s) to include (repeatable; default: *.py)
--reload-exclude        Glob pattern(s) to exclude (repeatable)
```

## Next steps

- Review the system configuration defaults in `src/pypnm_cmts/settings/system.json`.
- Check the FastAPI reference for available endpoints.
