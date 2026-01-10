# Phase 11 RxMER Router Deep Analysis (PyPNM)

## 1) Entry Point Summary

### Call sequence (get_capture -> analysis)

Entry: `RxMerRouter.__routes().get_capture()` in `src/pypnm/api/routes/docs/pnm/ds/ofdm/rxmer/router.py`.

Sequence:
1) `RxMerRouter.__routes().get_capture()`
   - Extracts `mac`, `ip`, `community`, `tftp_servers` from request.
   - Builds `CableModem` with `MacAddress(mac)`, `Inet(ip)`, `write_community=community`.
   - Runs `CableModemServicePreCheck(cable_modem=cm, validate_ofdm_exist=True).run_precheck()`.
   - Creates `CmDsOfdmRxMerService(cm, tftp_servers)`.
   - Reads `channel_ids = request.cable_modem.pnm_parameters.capture.channel_ids`.
   - Computes `interface_parameters = _resolve_interface_parameters(channel_ids)`.
   - Awaits `service.set_and_go(interface_parameters=interface_parameters)`.
   - Calls `service.getPnmMeasurementStatistics(channel_ids=channel_ids)`.
   - Creates `CommonProcessService(msg_rsp)` and calls `process()`.
   - Runs `Analysis(AnalysisType.BASIC, msg_rsp)`.
   - Returns JSON, archive, or invalid output response.

2) `CableModemServicePreCheck.run_precheck()` in `src/pypnm/api/routes/common/classes/operation/cable_modem_precheck.py`
   - ICMP ping via `cm.is_ping_reachable()`.
   - SNMP readiness via `cm.is_snmp_reachable()`.
   - MAC check unless `ignore_mac_address_check`.
   - Validates OFDM existence when `validate_ofdm_exist=True` (calls `validate_ofdm_channel_exist()` internally).

3) `CmDsOfdmRxMerService.set_and_go()` in `src/pypnm/api/routes/common/extended/common_measure_service.py`
   - Ping/SNMP checks (again via `is_ping_reachable`, `is_snmp_ready`).
   - Configures TFTP server (`cm.setDocsPnmBulk(tftp_server.inet, tftp_path)`).
   - Calls `_get_indexes_via_pnm_test_type(interface_parameters)` to pick channel indexes.
   - Runs `_pnm_measure_status_and_pnm_file_transfer()` to trigger capture and fetch files.

4) `CmDsOfdmRxMerService.getPnmMeasurementStatistics(channel_ids=...)` in `src/pypnm/api/routes/common/extended/common_measure_service.py`
   - For RxMER (`DocsPnmCmCtlTest.DS_OFDM_RXMER_PER_SUBCAR`), calls `cm.getDocsPnmCmDsOfdmRxMerEntry()` and then `_filter_measurement_entries(entries, channel_ids)`.

5) `CommonProcessService.process()` in `src/pypnm/api/routes/common/extended/common_process_service.py`
   - Reads PNM files from `SystemConfigSettings.pnm_dir()` and parses binary files via `CmDsOfdmRxMer`.

6) `Analysis(AnalysisType.BASIC, msg_rsp)` in `src/pypnm/api/routes/common/classes/analysis/analysis.py`
   - Converts parsed data into analysis results; for RxMER uses `CmDsOfdmRxMer` parsed output and model-specific processing.

## 2) Request Contract Trace

### Fields accessed in `get_capture()` (`rxmer/router.py`)

- `request.cable_modem.mac_address` → `MacAddressStr`
- `request.cable_modem.ip_address` → `InetAddressStr`
- `request.cable_modem.snmp` → `RequestDefaultsResolver.resolve_snmp_community()`
  - `RequestDefaultsResolver` reads `snmp.snmp_v2c.community` (nullable) and falls back to `SystemConfigSettings.snmp_write_community()`.
- `request.cable_modem.pnm_parameters.tftp` → `RequestDefaultsResolver.resolve_tftp_servers()`
  - Resolves TFTP IPv4/IPv6 from request or defaults (method-aware).
- `request.cable_modem.pnm_parameters.capture.channel_ids` → passed directly to interface parameter selection and measurement filtering.

### Presence/None behavior

- `request.cable_modem.pnm_parameters.capture` is always present by default in `PnmParameters` (`default_factory=PnmCaptureConfig`) in `src/pypnm/api/routes/common/classes/common_endpoint_classes/common_req_resp.py`.
- `PnmCaptureConfig.channel_ids` is `list[ChannelId] | None`, default `None` with a dedupe validator.
- Therefore, `request.cable_modem.pnm_parameters.capture` is non-null, but `channel_ids` may be `None` or empty.
- `RxMerRouter._resolve_interface_parameters(channel_ids)` returns `None` if `channel_ids` is falsey, which preserves "all channels" behavior.

## 3) Channel ID Handling (Current Behavior)

### Where channel_ids are read

- `rxmer/router.py`:
  - `channel_ids = request.cable_modem.pnm_parameters.capture.channel_ids`.
  - `_resolve_interface_parameters(channel_ids)` returns `DownstreamOfdmParameters(channel_id=list(channel_ids))` or `None`.

- `common_measure_service.py`:
  - `set_and_go(interface_parameters=...)` → `_get_indexes_via_pnm_test_type(interface_parameters)`.
  - `_get_indexes_via_pnm_test_type()` filters channel index/ID pairs when `ifParameters.channel_id` is provided.
  - `getPnmMeasurementStatistics(channel_ids=...)` → `_filter_measurement_entries(entries, channel_ids)` filters returned SNMP measurement entries.

### Effects of channel_ids

- **SNMP precheck behavior**: unaffected; precheck only validates channel existence but not specific channel_ids.
- **Interface parameter selection**: yes. When channel_ids present, `_get_indexes_via_pnm_test_type()` filters `idx_channelId` pairs to those channel_ids. This controls which captures are triggered.
- **Capture trigger step (set_and_go)**: yes. The filtered index list is passed into `_pnm_measure_status_and_pnm_file_transfer()` and only those channel ids are captured.
- **Measurement statistics fetch**: yes. `getPnmMeasurementStatistics(channel_ids=...)` filters entries post-capture.
- **Analysis downstream**: indirectly. Analysis reads the parsed data from captured files. If capture itself was filtered, analysis only sees those captures.

## 4) Candidate Implementation Points for Phase 10

### Option A (Best single point): `_get_indexes_via_pnm_test_type()` in `CommonMeasureService`

- **Where**: `src/pypnm/api/routes/common/extended/common_measure_service.py`.
- **Why**: This function controls which channel indexes are used for SNMP capture triggering. Filtering here ensures:
  - capture is limited to requested channel_ids;
  - no extra files are created;
  - downstream processing stays unchanged.
- **Pros**:
  - Centralized for all OFDM/OFDMA tests.
  - Already handles `channel_id_list` filtering.
  - Aligns with "all channels when None" default.
- **Cons**:
  - Requires trust that all tests use `set_and_go()` → `_get_indexes_via_pnm_test_type()` (true for RxMER here).

### Option B (Secondary): `RxMerRouter._resolve_interface_parameters()`

- **Where**: `src/pypnm/api/routes/docs/pnm/ds/ofdm/rxmer/router.py`.
- **Why**: It currently constructs `DownstreamOfdmParameters(channel_id=...)` only when channel_ids provided.
- **Pros**:
  - Localized to RxMER.
  - Minimal change and easy to reason about.
- **Cons**:
  - RxMER-specific; not reusable for other PNM endpoints.
  - Does not address filtering on the measurement statistics path (though `getPnmMeasurementStatistics` already filters).

**Recommendation**: Option A is the best single enforcement point for channel targeting at capture time, with Option B remaining a light, router-level pass-through.

## 5) Validation Expectations

### ChannelId range

- `ChannelId` is used as a type alias; numeric range is not enforced at the model level in this path.
- Channel IDs are sourced from CMTS/CM SNMP tables, so validity is generally "exists in CM channel ID table".
- `_get_indexes_via_pnm_test_type()` filters the CM’s reported `idx_channelId` list and returns `NO_OFDMA_CHAN_ID_INDEX_FOUND` if none exist.

### Best validation layer

- **Model layer**: `PnmCaptureConfig.channel_ids` currently only dedupes (see `RequestListNormalizer.dedupe_preserve_order`). No range validation.
- **Service layer**: `_get_indexes_via_pnm_test_type()` effectively validates by intersection with available channel IDs.

**Recommended**: Keep model validation minimal (dedupe), and treat "no matching channel IDs" as a service error via existing `ServiceStatusCode.NO_OFDMA_CHAN_ID_INDEX_FOUND` or similar. This aligns with existing service behavior and avoids breaking backward compatibility.

## 6) Test Plan (Pytest)

### Default behavior (no channel_ids)
- **Setup**: Request without `pnm_parameters.capture.channel_ids` or with empty list.
- **Assertions**:
  - `_resolve_interface_parameters()` returns `None`.
  - `_get_indexes_via_pnm_test_type()` returns the full index list for OFDM channels.
  - `getPnmMeasurementStatistics()` returns unfiltered entries.
- **Mocks**: Mock `CableModem` SNMP methods `getDocsIf31CmDsOfdmChannelIdIndexStack()` and `getDocsPnmCmDsOfdmRxMerEntry()`.

### Targeted behavior (channel_ids provided)
- **Setup**: Request with `channel_ids=[193]`.
- **Assertions**:
  - `_get_indexes_via_pnm_test_type()` filters index list to channel_id 193 only.
  - `_pnm_measure_status_and_pnm_file_transfer()` receives only that index.
  - `getPnmMeasurementStatistics(channel_ids)` returns only matching entries.
- **Mocks**: Same SNMP mocks; verify `filtered` list contents and lengths.

### Invalid channel_ids
- **Setup**: channel_ids not present in `idx_channelId` list.
- **Assertions**:
  - `_get_indexes_via_pnm_test_type()` returns SUCCESS with empty list or `NO_OFDMA_CHAN_ID_INDEX_FOUND` (current behavior returns `NO_OFDMA_CHAN_ID_INDEX_FOUND` when table empty; empty list when no match depending on inputs).
  - Endpoint returns appropriate error status (`SnmpResponse` with the returned status).

### IO and network mocks
- Mock SNMP methods and file retrieval to avoid actual IO:
  - `cm.getDocsIf31CmDsOfdmChannelIdIndexStack()`
  - `cm.getDocsPnmCmDsOfdmRxMerEntry()`
  - `cm.setDocsPnmBulk()`
  - `cm.getDocsPnmCmCtlStatus()`
  - `_check_and_wait_for_tftp_upload()` / `_get_and_move_pnm_file()`

## 7) Documentation Impact

- RxMER doc path referenced in router docstring:
  - `docs/api/fast-api/single/ds/ofdm/rxmer.md` (PyPNM repo).
- PNM request schema definitions:
  - `src/pypnm/api/routes/common/classes/common_endpoint_classes/common_req_resp.py` for `PnmCaptureConfig.channel_ids`.

**Documentation changes needed**:
- Update RxMER API doc to mention `pnm_parameters.capture.channel_ids` as optional list for targeted capture.
- If a flow diagram exists for RxMER capture, a Mermaid update could show the channel filter branching before capture.

## Notes on Current Behavior vs Desired Phase 11

- Channel targeting already affects capture triggering through `_get_indexes_via_pnm_test_type()` and results filtering through `getPnmMeasurementStatistics(channel_ids)`.
- If Phase 10 requires strict channel filtering regardless of measurement type, ensure that the interface-parameter path is used consistently across PNM endpoints.

