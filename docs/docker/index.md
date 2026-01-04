# Docker

This document describes the container startup flow and a minimal Docker run path.

## Startup Sequence

1) Load system configuration (system.json).
2) Validate `state_dir` and adapter settings.
3) Discover serving groups (SG IDs).
4) Create SGW store and manager.
5) Prime SGW cache once.
6) Start the SGW background refresh loop.

## Shutdown Sequence

1) Stop the SGW manager.
2) Stop and join the background refresh loop.

## Probes

- Liveness: `GET /ops/health` (process health only).
- Readiness: `GET /ops/ready` (SG discovery + SGW cache primed).

## Local Docker Run

This repo does not ship a Dockerfile. If you build your own image, ensure:

- `PYTHONPATH` includes `src/`.
- A writable volume is mounted at the configured `state_dir` (default: `.data/coordination`).
- Adapter settings point at the target CMTS (hostname and community).

Example run pattern (adjust paths for your image):

```bash
docker run --rm -p 8000:8000 \
  -v "$(pwd)/.data/coordination:/app/.data/coordination" \
  <your-image> \
  pypnm-cmts serve --host 0.0.0.0 --port 8000
```

Use the configuration file or environment overrides to set:

- CMTS hostname (example: `192.168.0.100`)
- SNMP community (example: `public`)
