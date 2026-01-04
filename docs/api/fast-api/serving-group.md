# Serving Group Endpoints

Cache-First Serving Group Endpoints Backed By SGW Snapshots. These endpoints do not trigger discovery or refresh; they return the latest cached snapshot and metadata.

## Common Fields

Response payloads include:

- `timestamp` ISO-8601 response timestamp
- `metadata.snapshot_time_epoch` epoch seconds for the cached snapshot
- `metadata.age_seconds` elapsed seconds since snapshot time, computed at request time
- `metadata.refresh_state` one of `OK`, `STALE`, or `ERROR`
- `metadata.last_error` bounded error message when present

Unless otherwise noted, examples use:

- MAC address: `aa:bb:cc:dd:ee:ff`
- IPv4 address: `192.168.0.100`

## GET /cmts/servingGroup/status

Return SGW Startup And Cache Readiness Status. This endpoint reports the discovered SG count, cache readiness, missing cache entries, and whether the background refresh loop is running.

Response:

```json
{
  "status": 0,
  "message": "sgw cache not ready",
  "timestamp": "2026-01-03T05:05:45.760643+00:00",
  "startup_status": {
    "startup_completed": true,
    "discovery_ok": true,
    "discovered_sg_ids": [1, 2],
    "last_refresh_epoch": 1767416694.071116,
    "error_message": "",
    "prime_failed": false
  },
  "refresh_running": false,
  "discovered_count": 2,
  "cache_ready": false,
  "missing_sg_ids": [2]
}
```

## POST /cmts/servingGroup/get/ids

Return Discovered Service Group Identifiers And Per-SG Cache Summaries. This endpoint returns HTTP 200 with `status` set to success even when `sgw_ready` is false; in that case, `message` is non-empty and summaries for missing snapshots report `refresh_state=ERROR` with a bounded `last_error`.

Request body:

```json
{}
```

Response:

```json
{
  "status": 0,
  "message": "",
  "timestamp": "2026-01-03T05:05:45.760643+00:00",
  "discovered_sg_ids": [1, 2],
  "sgw_ready": true,
  "summaries": [
    {
      "sg_id": 1,
      "metadata": {
        "snapshot_time_epoch": 1767416694.071116,
        "age_seconds": 0,
        "last_heavy_refresh_epoch": 1767416694.071116,
        "last_light_refresh_epoch": 1767416694.071116,
        "refresh_state": "OK",
        "last_error": null
      }
    }
  ]
}
```

## POST /cmts/servingGroup/get/cableModems

Return Cached Cable Modem Membership For A Service Group. Requires `sg_id`. Pagination is stable and deterministic.
When the snapshot is missing, `status` is `FAILURE`, `message` indicates the snapshot is not available, and `metadata.refresh_state` is `ERROR` with a bounded `last_error` (for store or snapshot gaps).

Request body:

```json
{
  "sg_id": 1,
  "page": 1,
  "page_size": 100
}
```

Response:

```json
{
  "status": 0,
  "message": "",
  "timestamp": "2026-01-03T06:39:23.046738+00:00",
  "sg_id": 1,
  "page": 1,
  "page_size": 100,
  "total_count": 1,
  "items": [
    {
      "mac": "aa:bb:cc:dd:ee:ff",
      "ipv4": "192.168.0.100",
      "ipv6": ""
    }
  ],
  "metadata": {
    "snapshot_time_epoch": 1767417069.3638031,
    "age_seconds": 0,
    "last_heavy_refresh_epoch": 1767417069.3638031,
    "last_light_refresh_epoch": 1767417069.3638031,
    "refresh_state": "OK",
    "last_error": null
  }
}
```

## POST /cmts/servingGroup/get/topology

Return Cached Topology Summary For A Service Group. Requires `sg_id`.
When the snapshot is missing, `status` is `FAILURE`, `message` indicates the snapshot is not available, and `metadata.refresh_state` is `ERROR` with a bounded `last_error` (for store or snapshot gaps).

Request body:

```json
{
  "sg_id": 1
}
```

Response:

```json
{
  "status": 0,
  "message": "",
  "timestamp": "2026-01-03T05:05:45.760643+00:00",
  "sg_id": 1,
  "topology": {
    "sg_id": 1,
    "ds_channels": {
      "count": 0,
      "channel_ids": []
    },
    "us_channels": {
      "count": 0,
      "channel_ids": []
    }
  },
  "metadata": {
    "snapshot_time_epoch": 1767416694.071116,
    "age_seconds": 0,
    "last_heavy_refresh_epoch": 1767416694.071116,
    "last_light_refresh_epoch": 1767416694.071116,
    "refresh_state": "OK",
    "last_error": null
  }
}
```
