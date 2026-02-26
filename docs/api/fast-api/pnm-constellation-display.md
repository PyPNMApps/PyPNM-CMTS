<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Maurice Garcia -->

# ConstellationDisplay Orchestration Endpoints

ConstellationDisplay serving-group orchestration uses a filesystem-backed operation model. The CMTS API creates and tracks job state while PyPNM captures are executed later in the pipeline.

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

## POST /cmts/pnm/sg/ds/ofdm/constellationDisplay/startCapture

Create a new serving-group ConstellationDisplay operation. The response returns a new `operation_id` and initial counters.

### Usage

```bash
curl -X POST http://127.0.0.1:8000/cmts/pnm/sg/ds/ofdm/constellationDisplay/startCapture \
  -H "content-type: application/json" \
  -d '{"capture_settings":{"modulation_order_offset":12,"number_sample_symbol":8192}}'
```

## POST /cmts/pnm/sg/ds/ofdm/constellationDisplay/status

Return the persisted operation state.

### Usage

```bash
curl -X POST http://127.0.0.1:8000/cmts/pnm/sg/ds/ofdm/constellationDisplay/status \
  -H "content-type: application/json" \
  -d '{"pnm_capture_operation_id":"<operation_id>"}'
```

## POST /cmts/pnm/sg/ds/ofdm/constellationDisplay/results

Return structured ConstellationDisplay results for an operation plus compatibility linkage records.
`results` supports the nested request shape (`operation`, `selection`, `analysis`, `output`) and still accepts the legacy flat `pnm_capture_operation_id` body.

### Usage

```bash
curl -X POST http://127.0.0.1:8000/cmts/pnm/sg/ds/ofdm/constellationDisplay/results \
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
      "capture_type": "CONSTELLATION_DISPLAY",
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
                "constellation_display_data": {
                  "file": {
                    "transaction_id": "9e95d2358b02f317",
                    "filename": "ds_constellation_display_606c63f48fb8_160_1772081353.bin"
                  },
                  "stage_status_codes": {
                    "eligibility": 0,
                    "precheck": 0,
                    "capture": 0
                  },
                  "stage_messages": null,
                  "pnm_file_type": "DOWNSTREAM_CONSTELLATION_DISPLAY",
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

## POST /cmts/pnm/sg/ds/ofdm/constellationDisplay/cancel

Request cancellation for an operation.

### Usage

```bash
curl -X POST http://127.0.0.1:8000/cmts/pnm/sg/ds/ofdm/constellationDisplay/cancel \
  -H "content-type: application/json" \
  -d '{"pnm_capture_operation_id":"<operation_id>"}'
```
