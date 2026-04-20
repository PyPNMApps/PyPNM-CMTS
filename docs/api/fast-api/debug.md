# Debug Endpoints

Debug endpoints are development-only tools.
They are available only when PyPNM-CMTS is started with `pypnm-cmts serve --debug`.

## Endpoints

### POST /ops/debug/allocateMemory

Retained-memory trigger for RSS-guard testing.
This endpoint keeps the requested allocation alive inside the running process so the
web-service RSS guard can be exercised under real runtime conditions.

Example:

```bash
curl -s -X POST http://127.0.0.1:8000/ops/debug/allocateMemory \
  -H 'content-type: application/json' \
  -d '{"megabytes": 1700}'
```

Response shape:

```json
{
  "status": "ok",
  "timestamp": "2025-01-01T00:00:00+00:00",
  "meta": {
    "mode": "standalone",
    "election_name": "",
    "state_dir": ".data/coordination",
    "sg_id": null
  },
  "requested_megabytes": 1700,
  "rss_before_bytes": 329695232,
  "rss_after_bytes": 2118123520,
  "retained_bytes": 1782579200,
  "message": "Retained debug memory allocation in-process; wait for the RSS guard poll interval."
}
```

Notes:

- This is a debug-mode-only tool, not a normal operational action.
- The allocation is intentionally retained so the RSS guard can observe it on the next poll.
- After allocation, wait at least one guard poll interval before expecting a reload.
- When debug mode is off, `/ops/debug/...` routes are not advertised and return `404`.
