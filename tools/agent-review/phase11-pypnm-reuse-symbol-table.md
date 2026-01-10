<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Maurice Garcia -->

# Phase 11 PyPNM Reuse Symbol Table

## Reuse Map

| Phase 11 Need | PyPNM Symbol | Import Path | How To Reuse | Notes / Constraints |
| --- | --- | --- | --- | --- |
| Inet validation | Inet | from pypnm.lib.inet import Inet | Direct import | Raises ValueError on invalid InetAddressStr; use for validation, not re-parsing. |
| Inet/IP types | InetAddressStr, IPv4Str, IPv6Str | from pypnm.lib.types import InetAddressStr, IPv4Str, IPv6Str | Direct import | Keep IPs as typed strings; no custom parsing. |
| Inet utilities | InetGenerate | from pypnm.lib.inet_utils import InetGenerate | Direct import | Use for IP version checks or conversions if needed. |
| Epoch timestamp generation | Generate.time_stamp, TimeUnit | from pypnm.lib.utils import Generate, TimeUnit | Direct import | Use TimeUnit.SECONDS for epoch seconds; returns TimeStamp (int). |
| MAC validation/normalization | MacAddress, MacAddressFormat | from pypnm.lib.mac_address import MacAddress, MacAddressFormat | Direct import | MacAddress normalizes formats and outputs colon format via __str__/to_mac_format. |
| MAC type | MacAddressStr | from pypnm.lib.types import MacAddressStr | Direct import | Use in CMTS BaseModels. |
| SNMP config (snmpV2C casing, blank checks) | SNMPConfig, SNMPv2c | from pypnm.api.routes.common.classes.common_endpoint_classes.schema.base_snmp import SNMPConfig, SNMPv2c | Composition | SNMPConfig uses camelCase aliases; SNMPv2c rejects blank community strings. |
| TFTP config (blank checks) | TftpConfig | from pypnm.api.routes.common.classes.common_endpoint_classes.common_req_resp import TftpConfig | Composition | Rejects blank strings; null uses system.json defaults. |
| Channel id list | PnmCaptureConfig | from pypnm.api.routes.common.classes.common_endpoint_classes.common_req_resp import PnmCaptureConfig | Composition | Dedupe via RequestListNormalizer; empty means all channels. |
| Status codes | ServiceStatusCode | from pypnm.api.routes.common.service.status_codes import ServiceStatusCode | Direct import | Shared enum; PyPNM <= 9999. |
| Operation state | OperationState | from pypnm.api.routes.advance.common.operation_state import OperationState | Boundary conversion | Use where compatible with Phase 11 lifecycle states. |
| Transaction ID type | TransactionId | from pypnm.lib.types import TransactionId | Direct import | Use for JSONL linkage records and status mapping. |
| Operation ID type | OperationId | from pypnm.lib.types import OperationId | Direct import | Use only when returned by PyPNM engine classes. |
| File name types | FileName, FileNameStr | from pypnm.lib.types import FileName, FileNameStr | Direct import | Use for file metadata references. |
| Transaction record model | TransactionRecordModel | from pypnm.api.routes.common.classes.file_capture.types import TransactionRecordModel | Boundary conversion | Use when resolving transaction_id into full capture metadata. |
| Transaction DB access | PnmFileTransaction | from pypnm.api.routes.common.classes.file_capture.pnm_file_transaction import PnmFileTransaction | Direct import | Authoritative source for transaction_id records. |
| Transaction record parser | TransactionRecordParser | from pypnm.api.routes.common.classes.file_capture.transaction_record_parser import TransactionRecordParser | Direct import | Builds TransactionRecordModel from transaction_id. |
| Capture grouping resolver | OperationCaptureGroupResolver | from pypnm.api.routes.common.classes.file_capture.pnm_file_opearation import OperationCaptureGroupResolver | Direct import | Resolves operation_id -> capture_group -> transaction_ids when needed. |

## Do Not Re-Implement

- Inet/IP parsing and validation (Inet, InetGenerate, InetAddressStr/IPv4Str/IPv6Str).
- MAC parsing/normalization (MacAddress, MacAddressFormat, MacAddressStr).
- Epoch timestamp generation/normalization (Generate.time_stamp with TimeUnit.SECONDS).
- SNMP/TFTP blank/null validation and casing (SNMPConfig/SNMPv2c, TftpConfig).
- ServiceStatusCode definitions and semantics.
- TransactionId, OperationId, FileName typing and formats.
- file_capture transaction logging and transaction_db storage (PnmFileTransaction and related parsers).
- Any L1/L2/L3 CM interaction utilities already present in PyPNM (reachability, SNMP, file capture, polling).

## Transaction DB Integration Notes

- PyPNM `transaction_db` is authoritative for capture metadata.
- CMTS JSONL stores linkage records only (transaction_id + sg_id/mac/stage/outcome), not full file metadata.
- Link keys from `CmDsOfdmRxMerService.set_and_go(...)` response:
  - `MessageResponse.payload[*].message.transaction_id`
  - `MessageResponse.payload[*].message.filename`
  - `MessageResponse.status` (ServiceStatusCode) for overall status

## PyPNM Engine Only (No PyPNM FastAPI)

- PyPNM-CMTS must call PyPNM Python engine classes directly; do not call PyPNM FastAPI HTTP routes.
