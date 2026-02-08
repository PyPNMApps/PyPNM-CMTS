<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Maurice Garcia -->

# RxMER Orchestration Endpoints

RxMER serving-group orchestration uses a filesystem-backed operation model. The CMTS API creates and tracks job state while PyPNM captures are executed later in the pipeline.

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

## POST /cmts/pnm/sg/ds/ofdm/rxmer/startCapture

Create a new serving-group RxMER operation. The response returns a new `operation_id` and initial counters.
Status values use numeric `ServiceStatusCode`.

Current behavior (Step 3): startCapture schedules background execution and returns immediately. Status, cancel, and results operate on persisted state and JSONL linkage records. Cancel creates `cancel.flag` and transitions to `CANCELLING`, and the runner transitions to `CANCELLED` when it observes the flag.

Collect-only behavior (Step 9): PyPNM owns PNM artifacts in `.data/pnm/` and authoritative transaction records in `.data/db/transactions.json`. CMTS linkage records store transaction_id and filename pointers for later decode/analysis. See `docs/api/fast-api/pypnm-cmts/sg-operations.md` for the on-disk data model.

Runner-level failures: the runner may synthesize stage outcomes when a per-modem timeout or internal exception occurs. In those cases, `ELIGIBILITY` and `PRECHECK` may be marked successful even if they did not run, and `CAPTURE` carries the failure status. `failure_reason` provides a normalized diagnostic for timeouts or runner-level failures.

Status types: orchestration responses use numeric `ServiceStatusCode`. `PnmCaptureStatus` exists for other capture pipelines but is not used in RxMER orchestration responses.

### Usage

```bash
curl -X POST http://127.0.0.1:8000/cmts/pnm/sg/ds/ofdm/rxmer/startCapture \
  -H "content-type: application/json" \
  -d '{}'
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
  }
}
```

### Request Elements

| Field | Type | Required | Notes |
|---|---|---|---|
| `cmts.serving_group.id` | `array<int>` | no | Empty list means all serving groups. |
| `cmts.cable_modem.mac_address` | `array<string>` | no | Empty list means all modems in selected serving groups. |
| `cmts.cable_modem.pnm_parameters.tftp.ipv4` | `string or null` | conditional | If `tftp` is present, both `ipv4` and `ipv6` keys must be present. Use `null` for defaults. |
| `cmts.cable_modem.pnm_parameters.tftp.ipv6` | `string or null` | conditional | If `tftp` is present, both `ipv4` and `ipv6` keys must be present. Use `null` for defaults. |
| `cmts.cable_modem.pnm_parameters.capture.channel_ids` | `array<int> or null` | no | `null`, missing, or empty means all channels. |
| `cmts.cable_modem.snmp.snmpV2C.community` | `string or null` | conditional | If `snmpV2C` is present, `community` key must be present. Use `null` for defaults. |
| `execution.max_workers` | `int` | no | Must be greater than `0`. Default `16`. |
| `execution.retry_count` | `int` | no | Must be `0` or greater. Default `3`. |
| `execution.retry_delay_seconds` | `float` | no | Must be `0.0` or greater. Default `5.0`. |
| `execution.per_modem_timeout_seconds` | `float` | no | Must be greater than `0.0`. Default `30.0`. |
| `execution.overall_timeout_seconds` | `float` | no | Must be greater than `0.0`. Default `120.0`. |

### Response

```json
{
  "status": 0,
  "message": "",
  "operation": {
    "operation_id": "1b3f5f3d4f3c4ab29a9ff9a3f0b7c8d1",
    "state": "queued",
    "counters": {
      "total_modems": 0,
      "eligible_modems": 0,
      "precheck_passed": 0,
      "capture_started": 0,
      "completed": 0,
      "success": 0,
      "failed": 0,
      "skipped": 0
    },
    "timestamps": {
      "created_epoch": 1767444600,
      "started_epoch": 0,
      "updated_epoch": 1767444600,
      "finished_epoch": 0
    },
    "request_summary": {
      "serving_group_ids": [],
      "mac_addresses": [],
      "channel_ids": [],
      "execution": {
        "max_workers": 16,
        "retry_count": 3,
        "retry_delay_seconds": 5.0,
        "per_modem_timeout_seconds": 30.0,
        "overall_timeout_seconds": 120.0
      }
    },
    "error_summary": null
  }
}
```

### Response Elements

| Field | Type | Always Present | Notes |
|---|---|---|---|
| `status` | `int` | yes | Numeric `ServiceStatusCode`. |
| `message` | `string` | yes | Informational or error message. |
| `operation.operation_id` | `string` | yes | Operation identifier used by status, results, and cancel. |
| `operation.state` | `string` | yes | `queued`, `running`, `cancelling`, `cancelled`, `completed`, or `failed`. |
| `operation.counters` | `object` | yes | Progress counters for modem processing lifecycle. |
| `operation.timestamps` | `object` | yes | Epoch timestamps for operation lifecycle. |
| `operation.request_summary` | `object` | yes | Normalized request scope and execution settings captured at start. |
| `operation.error_summary` | `object or null` | yes | Non-null when operation enters a failed terminal state. |

## POST /cmts/pnm/sg/ds/ofdm/rxmer/status

Return the persisted operation state.
The request payload uses `pnm_capture_operation_id`, while the returned state uses `operation_id`.

### Usage

```bash
curl -X POST http://127.0.0.1:8000/cmts/pnm/sg/ds/ofdm/rxmer/status \
  -H "content-type: application/json" \
  -d '{"pnm_capture_operation_id":"<operation_id>"}'
```

### Request

```json
{
  "pnm_capture_operation_id": "1b3f5f3d4f3c4ab29a9ff9a3f0b7c8d1"
}
```

### Request Elements

| Field | Type | Required | Notes |
|---|---|---|---|
| `pnm_capture_operation_id` | `string` | yes | Operation identifier returned by `startCapture`. |

### Response

```json
{
  "status": 0,
  "message": "",
  "operation": {
    "operation_id": "1b3f5f3d4f3c4ab29a9ff9a3f0b7c8d1",
    "state": "queued",
    "counters": {
      "total_modems": 0,
      "eligible_modems": 0,
      "precheck_passed": 0,
      "capture_started": 0,
      "completed": 0,
      "success": 0,
      "failed": 0,
      "skipped": 0
    },
    "timestamps": {
      "created_epoch": 1767444600,
      "started_epoch": 0,
      "updated_epoch": 1767444600,
      "finished_epoch": 0
    },
    "request_summary": {
      "serving_group_ids": [],
      "mac_addresses": [],
      "channel_ids": [],
      "execution": {
        "max_workers": 16,
        "retry_count": 3,
        "retry_delay_seconds": 5.0,
        "per_modem_timeout_seconds": 30.0,
        "overall_timeout_seconds": 120.0
      }
    },
    "error_summary": null
  }
}
```

### Response Elements

| Field | Type | Always Present | Notes |
|---|---|---|---|
| `status` | `int` | yes | Numeric `ServiceStatusCode`. |
| `message` | `string` | yes | Informational or error message. |
| `operation` | `object or null` | yes | Operation snapshot; `null` when not found or unavailable. |

## POST /cmts/pnm/sg/ds/ofdm/rxmer/results

Return linkage records for an operation. The response includes records only when the dataset is small enough to inline.
The request payload uses `pnm_capture_operation_id`, while the returned state uses `operation_id`.

### Usage

```bash
curl -X POST http://127.0.0.1:8000/cmts/pnm/sg/ds/ofdm/rxmer/results \
  -H "content-type: application/json" \
  -d '{"pnm_capture_operation_id":"<operation_id>"}'
```

### Request

```json
{
  "pnm_capture_operation_id": "1b3f5f3d4f3c4ab29a9ff9a3f0b7c8d1"
}
```

### Request Elements

| Field | Type | Required | Notes |
|---|---|---|---|
| `pnm_capture_operation_id` | `string` | yes | Operation identifier returned by `startCapture`. |

### Response

```json
{
  "status": 0,
  "message": "no results recorded",
  "summary": {
    "record_count": 0,
    "included_count": 0,
    "files_scanned": 0
  },
  "records": []
}
```

### Response Elements

| Field | Type | Always Present | Notes |
|---|---|---|---|
| `status` | `int` | yes | Numeric `ServiceStatusCode`. |
| `message` | `string` | yes | Summary message such as no results recorded or success. |
| `summary.record_count` | `int` | yes | Total linkage records stored for the operation. |
| `summary.included_count` | `int` | yes | Records included in this API response. |
| `summary.files_scanned` | `int` | yes | Number of result files scanned. |
| `records[]` | `array<object>` | yes | Per-modem stage linkage records. |
| `records[].pnm_capture_operation_id` | `string` | conditional | Parent operation identifier for each record. |
| `records[].sg_id` | `int` | conditional | Serving group identifier for each record. |
| `records[].mac_address` | `string` | conditional | Cable modem MAC address. |
| `records[].ip_address` | `string or null` | conditional | Resolved modem IP when available. |
| `records[].stage` | `string` | conditional | Stage identifier such as `ELIGIBILITY`, `PRECHECK`, `CAPTURE`. |
| `records[].status_code` | `int` | conditional | Numeric `ServiceStatusCode` for that stage. |
| `records[].failure_reason` | `string or null` | conditional | Normalized runner failure reason when set. |
| `records[].transaction_ids` | `array<string>` | conditional | PyPNM transaction pointers. |
| `records[].filenames` | `array<string>` | conditional | PyPNM artifact filename pointers. |
| `records[].started_epoch` | `int` | conditional | Stage start epoch seconds. |
| `records[].finished_epoch` | `int` | conditional | Stage finish epoch seconds. |
| `records[].message` | `string` | conditional | Stage message or error detail. |

## POST /cmts/pnm/sg/ds/ofdm/rxmer/cancel

Request cancellation for an operation.
The request payload uses `pnm_capture_operation_id`, while the returned state uses `operation_id`.

### Usage

```bash
curl -X POST http://127.0.0.1:8000/cmts/pnm/sg/ds/ofdm/rxmer/cancel \
  -H "content-type: application/json" \
  -d '{"pnm_capture_operation_id":"<operation_id>"}'
```

### Request

```json
{
  "pnm_capture_operation_id": "1b3f5f3d4f3c4ab29a9ff9a3f0b7c8d1"
}
```

### Request Elements

| Field | Type | Required | Notes |
|---|---|---|---|
| `pnm_capture_operation_id` | `string` | yes | Operation identifier returned by `startCapture`. |

### Response

```json
{
  "status": 0,
  "message": "",
  "operation": {
    "operation_id": "1b3f5f3d4f3c4ab29a9ff9a3f0b7c8d1",
    "state": "cancelling",
    "counters": {
      "total_modems": 0,
      "eligible_modems": 0,
      "precheck_passed": 0,
      "capture_started": 0,
      "completed": 0,
      "success": 0,
      "failed": 0,
      "skipped": 0
    },
    "timestamps": {
      "created_epoch": 1767444600,
      "started_epoch": 0,
      "updated_epoch": 1767444610,
      "finished_epoch": 0
    },
    "request_summary": {
      "serving_group_ids": [],
      "mac_addresses": [],
      "channel_ids": [],
      "execution": {
        "max_workers": 16,
        "retry_count": 3,
        "retry_delay_seconds": 5.0,
        "per_modem_timeout_seconds": 30.0,
        "overall_timeout_seconds": 120.0
      }
    },
    "error_summary": null
  }
}
```

### Response Elements

| Field | Type | Always Present | Notes |
|---|---|---|---|
| `status` | `int` | yes | Numeric `ServiceStatusCode`. |
| `message` | `string` | yes | Informational or error message. |
| `operation` | `object or null` | yes | Updated operation snapshot, usually with `state` set to `cancelling` when accepted. |
