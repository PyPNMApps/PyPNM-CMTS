<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Maurice Garcia -->

# FecSummary Orchestration Endpoints

FecSummary serving-group orchestration uses a filesystem-backed operation model. The CMTS API creates and tracks job state while PyPNM captures are executed later in the pipeline.

## Lifecycle

```mermaid
flowchart TD
    A[startCapture] --> B[state=QUEUED]
    B --> C[state=RUNNING]
    C --> D{cancel?}
    D -->|yes| E[cancel.flag set]
    E --> F[state=CANCELLING]
    F --> G[state=CANCELLED]
    D -->|no| G[state=COMPLETED]
    C --> H[state=FAILED]
    G --> I[results]
    F --> I
    H --> I
```

## POST /cmts/pnm/sg/ds/ofdm/fecSummary/startCapture

Create a new serving-group FecSummary operation. The response returns a new `operation_id` and initial counters.
Status values use numeric `ServiceStatusCode`.

Current behavior: startCapture schedules background execution and returns immediately. Status, cancel, and results operate on persisted state and JSONL linkage records.

### Usage

```bash
curl -X POST http://127.0.0.1:8000/cmts/pnm/sg/ds/ofdm/fecSummary/startCapture \
  -H "content-type: application/json" \
  -d '{"capture_settings":{"fec_summary_type":2}}'
```

### Request

```json
{
  "cmts": {
    "serving_group": { "id": [] },
    "cable_modem": {
      "mac_address": [],
      "pnm_parameters": {
        "tftp": { "ipv4": null, "ipv6": null },
        "capture": { "channel_ids": [] }
      },
      "snmp": { "snmpV2C": { "community": "public" } }
    }
  },
  "execution": {
    "max_workers": 16,
    "retry_count": 3,
    "retry_delay_seconds": 5.0,
    "per_modem_timeout_seconds": 30.0,
    "overall_timeout_seconds": 120.0
  },
  "capture_settings": {
    "fec_summary_type": 2
  }
}
```

### Request Elements

| Field | Type | Required | Notes |
|---|---|---|---|
| `cmts.serving_group.id` | `array<int>` | no | Empty list means all serving groups. |
| `cmts.cable_modem.mac_address` | `array<string>` | no | Empty list means all modems in selected serving groups. |
| `cmts.cable_modem.pnm_parameters.capture.channel_ids` | `array<int> or null` | no | `null`, missing, or empty means all channels. |
| `execution.*` | `object` | no | Standard SG orchestration execution controls. |
| `capture_settings.fec_summary_type` | `int` | no | FEC summary interval type. `2 = 10 min`, `3 = 24 hr`. Default `2`. |

### Response

```json
{
  "status": 0,
  "message": "",
  "operation": {
    "operation_id": "1b3f5f3d4f3c4ab29a9ff9a3f0b7c8d1",
    "state": "queued"
  }
}
```

## POST /cmts/pnm/sg/ds/ofdm/fecSummary/status

Return the persisted operation state.

### Usage

```bash
curl -X POST http://127.0.0.1:8000/cmts/pnm/sg/ds/ofdm/fecSummary/status \
  -H "content-type: application/json" \
  -d '{"pnm_capture_operation_id":"<operation_id>"}'
```

## POST /cmts/pnm/sg/ds/ofdm/fecSummary/results

Return structured FecSummary results for an operation plus compatibility linkage records.
`results` supports the nested request shape (`operation`, `selection`, `analysis`, `output`) and still accepts the legacy flat `pnm_capture_operation_id` body.

### Usage

```bash
curl -X POST http://127.0.0.1:8000/cmts/pnm/sg/ds/ofdm/fecSummary/results \
  -H "content-type: application/json" \
  -d '{"operation":{"pnm_capture_operation_id":"<operation_id>"},"selection":{"serving_group_ids":[],"channel_ids":[],"mac_addresses":[]},"analysis":{"type":"basic"},"output":{"type":"json"}}'
```

### Response

```json
{
  "status": 0,
  "message": "",
  "results": {
    "capture_details": {
      "capture_type": "FEC_SUMMARY",
      "capture_time_epoch": 1772081360
    },
    "cmts": {
      "cmts_hostname": "172.19.124.6"
    },
    "channels": [],
    "serving_groups": [
      {
        "service_group_id": 3147522,
        "channels": [
          {
            "channel_id": 160,
            "service_group_id": 3147522,
            "cable_modems": [
              {
                "mac_address": "aa:bb:cc:dd:ee:ff",
                "system_description": {
                  "VENDOR": "LANCity",
                  "MODEL": "LCPET-3"
                },
                "status": "success",
                "message": "",
                "fec_summary_data": {
                  "file": {
                    "transaction_id": "9e95d2358b02f317",
                    "filename": "ds_ofdm_fec_summary_606c63f48fb8_160_1772081353.bin"
                  },
                  "stage_status_codes": {
                    "eligibility": 0,
                    "precheck": 0,
                    "capture": 0
                  },
                  "stage_messages": null,
                  "pnm_file_type": "OFDM_FEC_SUMMARY",
                  "analysis": {},
                  "analysis_error": null
                }
              }
            ]
          }
        ]
      }
    ]
  },
  "summary": {
    "record_count": 3,
    "included_count": 3,
    "files_scanned": 1
  },
  "records": []
}
```

## POST /cmts/pnm/sg/ds/ofdm/fecSummary/cancel

Request cancellation for an operation.

### Usage

```bash
curl -X POST http://127.0.0.1:8000/cmts/pnm/sg/ds/ofdm/fecSummary/cancel \
  -H "content-type: application/json" \
  -d '{"pnm_capture_operation_id":"<operation_id>"}'
```
