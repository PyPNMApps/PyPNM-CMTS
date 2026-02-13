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

## GET /cmts/servingGroup/get/ids

Return Discovered Service Group Identifiers And Per-SG Cache Summaries. This endpoint returns HTTP 200 with `status` set to success even when `sgw_ready` is false; in that case, `message` is non-empty and summaries for missing snapshots report `refresh_state=ERROR` with a bounded `last_error`.
Uses runtime CMTS adapter settings (hostname/community/port) from system.json/env/CLI; request body is not required.
Startup discovery mode controls whether SG IDs are enumerated via SNMP (default) or from a static list.

Example:

```bash
curl -s http://127.0.0.1:8000/cmts/servingGroup/get/ids
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

Return Cached Cable Modem Membership Grouped By Service Group. The request uses `cmts.serving_group.id` and is cache-first (no refresh controls).
When a snapshot is missing for a discovered SG, the group returns empty items and `metadata.refresh_state` is `ERROR` with a bounded `last_error`.
Channel set values are populated from CMTS registration status when available; defaults are `0` otherwise.
Registration status is returned as an object with numeric `status` and decoded `text` tokens; unknown values map to `other`.

Request body:

```json
{
  "cmts": {
    "serving_group": {
      "id": []
    }
  },
  "page": 1,
  "page_size": 100
}
```

Semantics:
- `cmts.serving_group.id: []` means all discovered service groups.
- `cmts.serving_group.id: [3147266]` means a single service group.
- `cmts.serving_group.id: [3147266, 3213825]` means multiple service groups.
- Unknown fields are ignored but not supported for this endpoint.

Response:

```json
{
  "status": 0,
  "message": "",
  "timestamp": "2026-01-03T06:39:23.046738+00:00",
  "requested_sg_ids": [],
  "resolved_sg_ids": [3147266, 3213825],
  "missing_sg_ids": [],
  "groups": [
    {
      "sg_id": 3147266,
      "page": 1,
      "page_size": 100,
      "total_items": 1,
      "total_pages": 1,
      "items": [
        {
          "mac_address": "aa:bb:cc:dd:ee:ff",
          "ipv4": "192.168.0.100",
          "ipv6": "",
          "ds_channel_ids": [10],
          "us_channel_ids": [20],
          "registration_status": {
            "status": 8,
            "text": "operational"
          }
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
  ]
}
```

Example: single SG id

```json
{
  "cmts": {
    "serving_group": {
      "id": [3147266]
    }
  },
  "page": 1,
  "page_size": 100
}
```

Example: multiple SG ids

```json
{
  "cmts": {
    "serving_group": {
      "id": [3147266, 3213825]
    }
  },
  "page": 1,
  "page_size": 100
}
```

## POST /cmts/servingGroup/get/topology

Return RF topology and cable-modem membership for one service group or all discovered service groups.
Endpoint Constraints: empty list means all service groups; a single id returns one group; multiple ids are rejected.
This endpoint is cache-first and does not block waiting for refresh completion.

Request body:

```json
{
  "cmts": {
    "serving_group": {
      "id": []
    }
  },
  "page": 1,
  "page_size": 100
}
```

## POST /cmts/servingGroup/cableModem/docsDevResetNow

Issue `docsDevResetNow` to cable modems resolved from serving-group and MAC scope.
This endpoint is cache-backed for scope resolution and then sends per-modem SNMP reset commands.

Request body:

```json
{
  "cmts": {
    "serving_group": {
      "id": []
    },
    "cable_modem": {
      "mac_address": [],
      "snmp": {
        "snmpV2C": {
          "community": "private"
        }
      }
    }
  }
}
```

Semantics:
- `cmts.serving_group.id: []` means all discovered service groups.
- `cmts.cable_modem.mac_address: []` means all cable modems in resolved service groups.
- `cmts.cable_modem.snmp.snmpV2C.community` is optional; system default write community is used when omitted or null.
- `pnm_parameters` is not part of this endpoint request.

Response:

```json
{
  "status": 0,
  "message": "",
  "timestamp": "2026-02-13T20:15:30+00:00",
  "requested_sg_ids": [3147266],
  "requested_mac_addresses": ["aa:bb:cc:dd:ee:02"],
  "resolved_sg_ids": [3147266],
  "resolved_mac_addresses": ["aa:bb:cc:dd:ee:02"],
  "missing_sg_ids": [],
  "missing_mac_addresses": [],
  "attempted_count": 1,
  "success_count": 1,
  "failure_count": 0,
  "results": [
    {
      "sg_id": 3147266,
      "mac_address": "aa:bb:cc:dd:ee:02",
      "ip_address": "192.168.0.102",
      "status": 0,
      "message": "docsDevResetNow command sent"
    }
  ]
}
```

Single service group request:

```json
{
  "cmts": {
    "serving_group": {
      "id": [3147266]
    }
  },
  "page": 1,
  "page_size": 100
}
```

Invalid request (multiple ids):

```json
{
  "cmts": {
    "serving_group": {
      "id": [3147266, 3213825]
    }
  }
}
```

Response (grouped by service group). OFDMA entries omit center_frequency_hz and start_frequency_hz; use lower_frequency_hz, upper_frequency_hz, and channel_width_hz.

```json
{
  "status": 0,
  "message": "",
  "timestamp": "2026-01-03T05:05:45.760643+00:00",
  "requested_sg_ids": [],
  "resolved_sg_ids": [3147266],
  "missing_sg_ids": [],
  "groups": [
    {
      "sg_id": 3147266,
      "ds_ch_set_id": 10,
      "us_ch_set_id": 20,
      "channels": {
        "ds": {
          "sc_qam": [
            {
              "channel_id": 1,
              "channel_type": "sc_qam",
              "center_frequency_hz": 300000000,
              "channel_width_hz": 6000000,
              "lower_frequency_hz": 297000000,
              "upper_frequency_hz": 303000000
            }
          ],
          "ofdm": [
            {
              "channel_id": 33,
              "channel_type": "ofdm",
              "plc_frequency_hz": 330000000,
              "channel_width_hz": null,
              "lower_frequency_hz": 300000000,
              "upper_frequency_hz": 400000000
            }
          ],
          "counts": [
            {
              "channel_id": 1,
              "modem_count": 2
            },
            {
              "channel_id": 33,
              "modem_count": 2
            }
          ],
          "set_counts": [
            {
              "ch_set_id": 10,
              "modem_count": 2
            }
          ]
        },
        "us": {
          "sc_qam": [
            {
              "channel_id": 5,
              "channel_type": "sc_qam",
              "center_frequency_hz": 50000000,
              "channel_width_hz": 6400000,
              "lower_frequency_hz": 46800000,
              "upper_frequency_hz": 53200000
            }
          ],
          "ofdma": [],
          "counts": [
            {
              "channel_id": 5,
              "modem_count": 2
            }
          ],
          "set_counts": [
            {
              "ch_set_id": 20,
              "modem_count": 2
            }
          ]
        }
      },
      "page": 1,
      "page_size": 100,
      "total_items": 2,
      "total_pages": 1,
      "modems": ["aa:bb:cc:dd:ee:01", "aa:bb:cc:dd:ee:ff"],
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
