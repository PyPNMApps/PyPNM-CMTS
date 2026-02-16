# SG PNM Operations

Serving-group PNM operations share the same orchestration contract:

- `POST .../startCapture` creates an operation and returns `operation_id`
- `POST .../status` returns persisted operation state
- `POST .../results` returns linkage records (`transaction_ids`, `filenames`)
- `POST .../cancel` requests cooperative cancellation

All SG PNM endpoints are JSON-only and use numeric `ServiceStatusCode`.

## Common Request Bodies

`startCapture`:

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

`status`, `results`, `cancel`:

```json
{
  "pnm_capture_operation_id": "<operation_id>"
}
```

## Endpoint Families

### DS OFDM RxMER

- `POST /cmts/pnm/sg/ds/ofdm/rxmer/startCapture`
- `POST /cmts/pnm/sg/ds/ofdm/rxmer/status`
- `POST /cmts/pnm/sg/ds/ofdm/rxmer/results`
- `POST /cmts/pnm/sg/ds/ofdm/rxmer/cancel`

### DS Histogram

- `POST /cmts/pnm/sg/ds/histogram/startCapture`
- `POST /cmts/pnm/sg/ds/histogram/status`
- `POST /cmts/pnm/sg/ds/histogram/results`
- `POST /cmts/pnm/sg/ds/histogram/cancel`

Downstream histogram accepts optional capture settings on `startCapture`:

```json
{
  "capture_settings": {
    "sample_duration": 10
  }
}
```

### DS OFDM ChannelEstCoeff

- `POST /cmts/pnm/sg/ds/ofdm/channelEstCoeff/startCapture`
- `POST /cmts/pnm/sg/ds/ofdm/channelEstCoeff/status`
- `POST /cmts/pnm/sg/ds/ofdm/channelEstCoeff/results`
- `POST /cmts/pnm/sg/ds/ofdm/channelEstCoeff/cancel`

### DS OFDM FecSummary

- `POST /cmts/pnm/sg/ds/ofdm/fecSummary/startCapture`
- `POST /cmts/pnm/sg/ds/ofdm/fecSummary/status`
- `POST /cmts/pnm/sg/ds/ofdm/fecSummary/results`
- `POST /cmts/pnm/sg/ds/ofdm/fecSummary/cancel`

### DS OFDM ConstellationDisplay

- `POST /cmts/pnm/sg/ds/ofdm/constellationDisplay/startCapture`
- `POST /cmts/pnm/sg/ds/ofdm/constellationDisplay/status`
- `POST /cmts/pnm/sg/ds/ofdm/constellationDisplay/results`
- `POST /cmts/pnm/sg/ds/ofdm/constellationDisplay/cancel`

Constellation display also accepts optional capture settings on `startCapture`:

```json
{
  "capture_settings": {
    "modulation_order_offset": 12,
    "number_sample_symbol": 8192
  }
}
```

### DS OFDM ModulationProfile

- `POST /cmts/pnm/sg/ds/ofdm/modulationProfile/startCapture`
- `POST /cmts/pnm/sg/ds/ofdm/modulationProfile/status`
- `POST /cmts/pnm/sg/ds/ofdm/modulationProfile/results`
- `POST /cmts/pnm/sg/ds/ofdm/modulationProfile/cancel`

### Full Bandwidth SpectrumAnalyzer

- `POST /cmts/pnm/sg/spectrumAnalyzer/startCapture`
- `POST /cmts/pnm/sg/spectrumAnalyzer/status`
- `POST /cmts/pnm/sg/spectrumAnalyzer/results`
- `POST /cmts/pnm/sg/spectrumAnalyzer/cancel`

Full bandwidth spectrum analyzer accepts optional capture settings on `startCapture`:

```json
{
  "capture_settings": {
    "inactivity_timeout": 60,
    "first_segment_center_freq": 300000000,
    "last_segment_center_freq": 900000000,
    "resolution_bw": 30000,
    "noise_bw": 150,
    "window_function": 2,
    "num_averages": 1,
    "spectrum_retrieval_type": 1
  }
}
```

### DS OFDM SpectrumAnalyzer

- `POST /cmts/pnm/sg/ds/ofdm/spectrumAnalyzer/startCapture`
- `POST /cmts/pnm/sg/ds/ofdm/spectrumAnalyzer/status`
- `POST /cmts/pnm/sg/ds/ofdm/spectrumAnalyzer/results`
- `POST /cmts/pnm/sg/ds/ofdm/spectrumAnalyzer/cancel`

DS OFDM spectrum analyzer accepts optional capture settings on `startCapture`:

```json
{
  "capture_settings": {
    "number_of_averages": 10,
    "resolution_bandwidth_hz": 25000,
    "spectrum_retrieval_type": 1
  }
}
```

### DS SCQAM SpectrumAnalyzer

- `POST /cmts/pnm/sg/ds/scqam/spectrumAnalyzer/startCapture`
- `POST /cmts/pnm/sg/ds/scqam/spectrumAnalyzer/status`
- `POST /cmts/pnm/sg/ds/scqam/spectrumAnalyzer/results`
- `POST /cmts/pnm/sg/ds/scqam/spectrumAnalyzer/cancel`

DS SCQAM spectrum analyzer accepts optional capture settings on `startCapture`:

```json
{
  "capture_settings": {
    "number_of_averages": 10,
    "resolution_bandwidth_hz": 25000,
    "spectrum_retrieval_type": 1
  }
}
```

### US OFDMA PreEqualization

- `POST /cmts/pnm/sg/us/ofdma/preEqualization/startCapture`
- `POST /cmts/pnm/sg/us/ofdma/preEqualization/status`
- `POST /cmts/pnm/sg/us/ofdma/preEqualization/results`
- `POST /cmts/pnm/sg/us/ofdma/preEqualization/cancel`

Pre-equalization capture can produce multiple files per modem. `results` returns all collected `transaction_ids` and `filenames`.

## Usage Examples

Start a constellation display operation:

```bash
curl -X POST http://127.0.0.1:8000/cmts/pnm/sg/ds/ofdm/constellationDisplay/startCapture \
  -H "content-type: application/json" \
  -d '{"capture_settings":{"modulation_order_offset":12,"number_sample_symbol":8192}}'
```

Start a downstream histogram operation:

```bash
curl -X POST http://127.0.0.1:8000/cmts/pnm/sg/ds/histogram/startCapture \
  -H "content-type: application/json" \
  -d '{"capture_settings":{"sample_duration":10}}'
```

Fetch status for any operation:

```bash
curl -X POST http://127.0.0.1:8000/cmts/pnm/sg/us/ofdma/preEqualization/status \
  -H "content-type: application/json" \
  -d '{"pnm_capture_operation_id":"<operation_id>"}'
```

Fetch results for any operation:

```bash
curl -X POST http://127.0.0.1:8000/cmts/pnm/sg/ds/ofdm/fecSummary/results \
  -H "content-type: application/json" \
  -d '{"pnm_capture_operation_id":"<operation_id>"}'
```

Cancel any operation:

```bash
curl -X POST http://127.0.0.1:8000/cmts/pnm/sg/ds/ofdm/modulationProfile/cancel \
  -H "content-type: application/json" \
  -d '{"pnm_capture_operation_id":"<operation_id>"}'
```

Start full bandwidth spectrum analyzer operation:

```bash
curl -X POST http://127.0.0.1:8000/cmts/pnm/sg/spectrumAnalyzer/startCapture \
  -H "content-type: application/json" \
  -d '{"capture_settings":{"first_segment_center_freq":300000000,"last_segment_center_freq":900000000,"resolution_bw":30000}}'
```

For a full response walkthrough, see [RxMER deep dive](pnm-rxmer.md).
