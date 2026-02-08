# CLI Examples

Use These Examples To Fetch CMTS Data Via SNMP.

## Table Of Contents

- [Assumptions](#assumptions)
- [CLI Usage](#cli-usage)
- [Get sysDescr (SNMPv2c)](#get-sysdescr-snmpv2c)
- [Get docsIf3MdNodeStatusMdDsSgId (SNMPv2c)](#get-docsif3mdnodestatusmddssgid-snmpv2c)
- [Get docsIf3MdNodeStatusMdUsSgId (SNMPv2c)](#get-docsif3mdnodestatusmdussgid-snmpv2c)
- [Get Service Group Topology (SNMPv2c)](#get-service-group-topology-snmpv2c)
- [Get docsIf3CmtsCmRegStatusMacAddr (SNMPv2c)](#get-docsif3cmtscmregstatusmacaddr-snmpv2c)
- [Get docsIf3CmtsCmRegStatusMdCmSgId Via MAC (SNMPv2c)](#get-docsif3cmtscmregstatusmdcmsgid-via-mac-snmpv2c)
- [Get All Registered CMs (SNMPv2c)](#get-all-registered-cms-snmpv2c)
- [Get Registered CM MAC And IP Tuples (SNMPv2c)](#get-registered-cm-mac-and-ip-tuples-snmpv2c)
- [Get CM Inet Addresses By MAC (SNMPv2c)](#get-cm-inet-addresses-by-mac-snmpv2c)
- [Get MD-CM-SG-ID By Node Name (SNMPv2c)](#get-md-cm-sg-id-by-node-name-snmpv2c)
- [Get CM Registration SG ID By Node Name (SNMPv2c)](#get-cm-registration-sg-id-by-node-name-snmpv2c)
- [Get CM Registration SG ID By DS SG ID (SNMPv2c)](#get-cm-registration-sg-id-by-ds-sg-id-snmpv2c)
- [Get docsPnmBulkDataTransferCfg Records (SNMPv2c)](#get-docspnmbulkdatatransfercfg-records-snmpv2c)
- [Get docsPnmCmtsUsOfdmaRxMer Records (SNMPv2c)](#get-docspnmcmtsusofdmarxmer-records-snmpv2c)
- [Discovery (CMTS Inventory)](#discovery-cmts-inventory)
- [Orchestrator Run Modes](#orchestrator-run-modes)
- [Next Steps](#next-steps)

## Assumptions

- Commands Are Run From The Repository Root.
- Python Is Available; Optional `.env` Activation Is Handled By Your Environment.

## CLI Usage

- JSON Is The Default Output For Example CLIs.
- Use `--text` For Flat Text Output.
- Use `--json-pretty` To Pretty-Print JSON Output.

Example:

```bash
CMTS_HOST="192.168.0.100"
SNMP_COMMUNITY="public"

clear && python src/pypnm_cmts/examples/cli/get_service_group_topology.py \
  --cmts-hostname "${CMTS_HOST}" \
  --cmts-community "${SNMP_COMMUNITY}" \
  --json-pretty
```

## Get sysDescr (SNMPv2c)

Fetch The CMTS `sysDescr` Via SNMPv2c. The Command Exits With Code `1` When The Response Is Empty Or The Request Fails. JSON Output Is The Default.

### Linux/macOS

```bash
CMTS_HOST="192.168.0.100"
SNMP_COMMUNITY="public"
SNMP_PORT=161

clear && python src/pypnm_cmts/examples/cli/get_sysdescr.py "${CMTS_HOST}" \
  -c "${SNMP_COMMUNITY}" \
  -p "${SNMP_PORT}"
```

Text output:

```bash
CMTS_HOST="192.168.0.100"
SNMP_COMMUNITY="public"

clear && python src/pypnm_cmts/examples/cli/get_sysdescr.py "${CMTS_HOST}" \
  -c "${SNMP_COMMUNITY}" \
  --text
```

### Windows PowerShell

```powershell
$env:CMTS_HOST = "192.168.0.100"
$env:SNMP_COMMUNITY = "public"
$env:SNMP_PORT = "161"

Clear-Host; python src/pypnm_cmts/examples/cli/get_sysdescr.py $env:CMTS_HOST -c $env:SNMP_COMMUNITY -p $env:SNMP_PORT
```

Text output:

```powershell
$env:CMTS_HOST = "192.168.0.100"
$env:SNMP_COMMUNITY = "public"

Clear-Host; python src/pypnm_cmts/examples/cli/get_sysdescr.py $env:CMTS_HOST -c $env:SNMP_COMMUNITY --text
```

### Output

- Text: `Cisco IOS Software [IOSXE], cBR Software (...)`
- JSON: `{"vendor":"Cisco","platform":"cBR Software (...)","software":"IOSXE","version":"17.15.1z","release":"fc3",...}`

## Get docsIf3MdNodeStatusMdDsSgId (SNMPv2c)

Fetch Downstream Service Group IDs For The Available MD Nodes.

```bash
CMTS_HOST="192.168.0.100"
SNMP_COMMUNITY="public"

clear && python src/pypnm_cmts/examples/cli/get_md_ds_sg_id.py \
  --cmts-hostname "${CMTS_HOST}" \
  --cmts-community "${SNMP_COMMUNITY}"
```

## Get docsIf3MdNodeStatusMdUsSgId (SNMPv2c)

Fetch Upstream Service Group IDs For The Available MD Nodes.

```bash
CMTS_HOST="192.168.0.100"
SNMP_COMMUNITY="public"

clear && python src/pypnm_cmts/examples/cli/get_md_us_sg_id.py \
  --cmts-hostname "${CMTS_HOST}" \
  --cmts-community "${SNMP_COMMUNITY}"
```

## Get Service Group Topology (SNMPv2c)

Fetch The CMTS Service-Group Topology (Default JSON Output).

```bash
CMTS_HOST="192.168.0.100"
SNMP_COMMUNITY="public"

clear && python src/pypnm_cmts/examples/cli/get_service_group_topology.py \
  --cmts-hostname "${CMTS_HOST}" \
  --cmts-community "${SNMP_COMMUNITY}"
```

Text output:

```bash
CMTS_HOST="192.168.0.100"
SNMP_COMMUNITY="public"

clear && python src/pypnm_cmts/examples/cli/get_service_group_topology.py \
  --cmts-hostname "${CMTS_HOST}" \
  --cmts-community "${SNMP_COMMUNITY}" \
  --text
```

## Get docsIf3CmtsCmRegStatusMacAddr (SNMPv2c)

Fetch CM Registration Status MAC Address Entries.

```bash
CMTS_HOST="192.168.0.100"
SNMP_COMMUNITY="public"

clear && python src/pypnm_cmts/examples/cli/get_cm_reg_status_mac_addr.py \
  --cmts-hostname "${CMTS_HOST}" \
  --cmts-community "${SNMP_COMMUNITY}"
```

## Get docsIf3CmtsCmRegStatusMdCmSgId Via MAC (SNMPv2c)

Fetch The Service Group ID For The First MAC Address Discovered In `docsIf3CmtsCmRegStatusMacAddr`.

```bash
CMTS_HOST="192.168.0.100"
SNMP_COMMUNITY="public"

clear && python src/pypnm_cmts/examples/cli/get_cm_reg_status_sg_id_via_mac.py \
  --cmts-hostname "${CMTS_HOST}" \
  --cmts-community "${SNMP_COMMUNITY}"
```

## Get All Registered CMs (SNMPv2c)

Fetch CM Registration Entries For All Serving Groups (Default JSON Output).

```bash
CMTS_HOST="192.168.0.100"
SNMP_COMMUNITY="public"

clear && python src/pypnm_cmts/examples/cli/get_all_registered_cm.py \
  --cmts-hostname "${CMTS_HOST}" \
  --cmts-community "${SNMP_COMMUNITY}"
```

Fetch CM Registration Entries For A Specific Serving Group:

```bash
CMTS_HOST="192.168.0.100"
SNMP_COMMUNITY="public"
SERVING_GROUP_ID=7

clear && python src/pypnm_cmts/examples/cli/get_all_registered_cm.py \
  --cmts-hostname "${CMTS_HOST}" \
  --cmts-community "${SNMP_COMMUNITY}" \
  --serving-group-id "${SERVING_GROUP_ID}"
```

## Get Registered CM MAC And IP Tuples (SNMPv2c)

Fetch CM MAC And IP Address Tuples For A Serving Group (Default JSON Output).

```bash
CMTS_HOST="192.168.0.100"
SNMP_COMMUNITY="public"
SERVING_GROUP_ID=7

clear && python src/pypnm_cmts/examples/cli/get_all_registered_cm_mac_inet.py \
  --cmts-hostname "${CMTS_HOST}" \
  --cmts-community "${SNMP_COMMUNITY}" \
  --serving-group-id "${SERVING_GROUP_ID}"
```

Fetch CM MAC And IP Address Tuples For All Serving Groups:

```bash
CMTS_HOST="192.168.0.100"
SNMP_COMMUNITY="public"

clear && python src/pypnm_cmts/examples/cli/get_all_registered_cm_mac_inet.py \
  --cmts-hostname "${CMTS_HOST}" \
  --cmts-community "${SNMP_COMMUNITY}"
```

## Get CM Inet Addresses By MAC (SNMPv2c)

Fetch CM Inet Addresses For A Specific MAC Address (Default JSON Output).

```bash
CMTS_HOST="192.168.0.100"
SNMP_COMMUNITY="public"
CM_MAC="aa:bb:cc:dd:ee:ff"

clear && python src/pypnm_cmts/examples/cli/get_cm_inet_address.py \
  --cmts-hostname "${CMTS_HOST}" \
  --cmts-community "${SNMP_COMMUNITY}" \
  --mac "${CM_MAC}"
```

Fetch CM Inet Addresses With Raw SNMP Values:

```bash
CMTS_HOST="192.168.0.100"
SNMP_COMMUNITY="public"
CM_MAC="aa:bb:cc:dd:ee:ff"

clear && python src/pypnm_cmts/examples/cli/get_cm_inet_address.py \
  --cmts-hostname "${CMTS_HOST}" \
  --cmts-community "${SNMP_COMMUNITY}" \
  --mac "${CM_MAC}" \
  --raw
```

## Get MD-CM-SG-ID By Node Name (SNMPv2c)

Fetch The MD-CM-SG-ID For A Given Node Name (Default JSON Output).

```bash
CMTS_HOST="192.168.0.100"
SNMP_COMMUNITY="public"
NODE_NAME="FN-1"

clear && python src/pypnm_cmts/examples/cli/get_md_cm_sg_id_from_node_name.py \
  --cmts-hostname "${CMTS_HOST}" \
  --cmts-community "${SNMP_COMMUNITY}" \
  --node-name "${NODE_NAME}"
```

## Get CM Registration SG ID By Node Name (SNMPv2c)

Fetch The CM Registration SG ID For A Given Node Name (Default JSON Output).

```bash
CMTS_HOST="192.168.0.100"
SNMP_COMMUNITY="public"
NODE_NAME="FN-1"

clear && python src/pypnm_cmts/examples/cli/get_cm_reg_sg_id_from_node_name.py \
  --cmts-hostname "${CMTS_HOST}" \
  --cmts-community "${SNMP_COMMUNITY}" \
  --node-name "${NODE_NAME}"
```

## Get CM Registration SG ID By DS SG ID (SNMPv2c)

Fetch The CM Registration SG ID For A Downstream SG ID Value (Default JSON Output).

```bash
CMTS_HOST="192.168.0.100"
SNMP_COMMUNITY="public"
DS_SG_ID=6

clear && python src/pypnm_cmts/examples/cli/get_cm_reg_sg_id_from_ds_sg_id.py \
  --cmts-hostname "${CMTS_HOST}" \
  --cmts-community "${SNMP_COMMUNITY}" \
  --ds-sg-id "${DS_SG_ID}"
```

## Get docsPnmBulkDataTransferCfg Records (SNMPv2c)

Fetch The Bulk Data Transfer Destination Configuration Table (Default JSON Output).

```bash
CMTS_HOST="192.168.0.100"
SNMP_COMMUNITY="public"

clear && python src/pypnm_cmts/examples/cli/get_docs_pnm_bulk_data_transfer_cfg_record.py \
  --cmts-hostname "${CMTS_HOST}" \
  --cmts-community "${SNMP_COMMUNITY}"
```

Pretty JSON output:

```bash
CMTS_HOST="192.168.0.100"
SNMP_COMMUNITY="public"

clear && python src/pypnm_cmts/examples/cli/get_docs_pnm_bulk_data_transfer_cfg_record.py \
  --cmts-hostname "${CMTS_HOST}" \
  --cmts-community "${SNMP_COMMUNITY}" \
  --json-pretty
```

## Get docsPnmCmtsUsOfdmaRxMer Records (SNMPv2c)

Fetch The CMTS US OFDMA RxMER Per-Channel Control Table (Default JSON Output).

```bash
CMTS_HOST="192.168.0.100"
SNMP_COMMUNITY="public"

clear && python src/pypnm_cmts/examples/cli/get_docs_pnm_cmts_us_ofdma_rxmer_record.py \
  --cmts-hostname "${CMTS_HOST}" \
  --cmts-community "${SNMP_COMMUNITY}"
```

Pretty JSON output:

```bash
CMTS_HOST="192.168.0.100"
SNMP_COMMUNITY="public"

clear && python src/pypnm_cmts/examples/cli/get_docs_pnm_cmts_us_ofdma_rxmer_record.py \
  --cmts-hostname "${CMTS_HOST}" \
  --cmts-community "${SNMP_COMMUNITY}" \
  --json-pretty
```

## Discovery (CMTS Inventory)

Discover Service Groups And Registered Cable Modems From The CMTS (Default JSON Output).
If `--write-community` is omitted or empty, the discovery path uses the effective read community.
`run` and `run-forever` load CMTS adapter settings from system.json unless you pass adapter overrides.

```bash
CMTS_HOST="192.168.0.100"
SNMP_COMMUNITY="public"

clear && pypnm-cmts discover \
  --cmts-hostname "${CMTS_HOST}" \
  --read-community "${SNMP_COMMUNITY}" \
  --state-dir ./.data/coordination
```

Text Output:

```bash
CMTS_HOST="192.168.0.100"
SNMP_COMMUNITY="public"

clear && pypnm-cmts discover \
  --cmts-hostname "${CMTS_HOST}" \
  --read-community "${SNMP_COMMUNITY}" \
  --write-community "private" \
  --state-dir ./.data/coordination \
  --text
```

## Orchestrator Run Modes

`pypnm-cmts` Supports One-Shot And Continuous Orchestrator Execution Modes.

- `run` executes a single coordination tick and prints JSON output.
- `run-forever` executes coordination ticks continuously and prints JSON output per tick.
By default, `run` and `run-forever` use CMTS adapter settings from system.json. Adapter overrides can be supplied via flags.

JSON output includes:

- `tick_index` (1-based tick index)
- `run_id` (worker ticks that execute work)
- `lease_held` (worker lease status for the tick)

One-shot runs report `tick_index` = 1.
Continuous runs increment `tick_index` once per tick in the same process.
Worker persistence happens only when `lease_held` is true.

Standalone mode (single tick):

```bash
clear && pypnm-cmts run --mode standalone
```

Standalone mode (continuous ticks):

```bash
clear && pypnm-cmts run-forever --mode standalone --tick-interval-seconds 1 --max-ticks 5
```

Controller mode (single tick):

```bash
clear && pypnm-cmts run --mode controller
```

Controller mode (continuous ticks):

```bash
clear && pypnm-cmts run-forever --mode controller
```

Worker mode (single tick, bound worker with numeric service group id):

```bash
clear && pypnm-cmts run --mode worker --sg-id 1
```

Worker mode (continuous ticks, bound worker with numeric service group id):

```bash
clear && pypnm-cmts run-forever --mode worker --sg-id 1
```

Worker mode (unbound, continuous ticks with inventory-derived service groups):

```bash
clear && pypnm-cmts run-forever --mode worker --max-ticks 5
```

Optional overrides (example):

```bash
clear && pypnm-cmts run --mode standalone \
  --config ./src/pypnm_cmts/settings/system.json \
  --owner-id owner-1 \
  --target-service-groups 2 \
  --shard-mode score \
  --tick-interval-seconds 1.0 \
  --leader-ttl-seconds 10 \
  --lease-ttl-seconds 10 \
  --cmts-hostname 192.168.0.100 \
  --read-community public \
  --write-community private \
  --snmp-port 161 \
  --state-dir ./.data/coordination \
  --election-name cmts-primary
```

## Next Steps

- Update The Python API Docs When New Parsers Or Data Models Are Added.
- Update The FastAPI Docs When Endpoints Are Introduced.
- Add A Short "Troubleshooting" Section Once You Have Common Failure Modes (SNMP Timeout, Missing MIB View, etc.).
