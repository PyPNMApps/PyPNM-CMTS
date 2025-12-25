# CLI examples

Use these examples to fetch CMTS data via SNMP.

## Get sysDescr (SNMPv2c)

Fetch the CMTS `sysDescr` via SNMPv2c. The command exits with code `1` when the
response is empty or the request fails. JSON output is the default.

### Linux/macOS

```bash
CMTS_HOST="192.168.0.100"
SNMP_COMMUNITY="public"
SNMP_PORT=161

python example/cli/get_sysdescr.py "${CMTS_HOST}" -c "${SNMP_COMMUNITY}" -p "${SNMP_PORT}"
```

Text output:

```bash
CMTS_HOST="192.168.0.100"
SNMP_COMMUNITY="public"

python example/cli/get_sysdescr.py "${CMTS_HOST}" -c "${SNMP_COMMUNITY}" --text
```

### Windows PowerShell

```powershell
$env:CMTS_HOST = "192.168.0.100"
$env:SNMP_COMMUNITY = "public"
$env:SNMP_PORT = "161"

python example/cli/get_sysdescr.py $env:CMTS_HOST -c $env:SNMP_COMMUNITY -p $env:SNMP_PORT
```

Text output:

```powershell
$env:CMTS_HOST = "192.168.0.100"
$env:SNMP_COMMUNITY = "public"

python example/cli/get_sysdescr.py $env:CMTS_HOST -c $env:SNMP_COMMUNITY --text
```

### Output

- Text: `Cisco IOS Software [IOSXE], cBR Software (...)`
- JSON: `{"vendor":"Cisco","platform":"cBR Software (...)","software":"IOSXE","version":"17.15.1z","release":"fc3",...}`

## Get docsIf3MdNodeStatusMdDsSgId (SNMPv2c)

Fetch downstream service group IDs for the available MD nodes.

```bash
CMTS_HOST="192.168.0.100"
SNMP_COMMUNITY="public"

python src/pypnm_cmts/examples/cli/get_md_ds_sg_id.py \
  --cmts-hostname "${CMTS_HOST}" \
  --cmts-community "${SNMP_COMMUNITY}"
```

## Get docsIf3MdNodeStatusMdUsSgId (SNMPv2c)

Fetch upstream service group IDs for the available MD nodes.

```bash
CMTS_HOST="192.168.0.100"
SNMP_COMMUNITY="public"

python src/pypnm_cmts/examples/cli/get_md_us_sg_id.py \
  --cmts-hostname "${CMTS_HOST}" \
  --cmts-community "${SNMP_COMMUNITY}"
```

## Get docsIf3CmtsCmRegStatusMacAddr (SNMPv2c)

Fetch CM registration status MAC address entries.

```bash
CMTS_HOST="192.168.0.100"
SNMP_COMMUNITY="public"

python src/pypnm_cmts/examples/cli/get_cm_reg_status_mac_addr.py \
  --cmts-hostname "${CMTS_HOST}" \
  --cmts-community "${SNMP_COMMUNITY}"
```

## Get docsIf3CmtsCmRegStatusMdCmSgId via MAC (SNMPv2c)

Fetch the service group ID for the first MAC address discovered in
`docsIf3CmtsCmRegStatusMacAddr`.

```bash
CMTS_HOST="192.168.0.100"
SNMP_COMMUNITY="public"

python src/pypnm_cmts/examples/cli/get_cm_reg_status_sg_id_via_mac.py \
  --cmts-hostname "${CMTS_HOST}" \
  --cmts-community "${SNMP_COMMUNITY}"
```

## Get all registered CMs (SNMPv2c)

Fetch CM registration entries for all serving groups (default JSON output).

```bash
CMTS_HOST="192.168.0.100"
SNMP_COMMUNITY="public"

python src/pypnm_cmts/examples/cli/get_all_registered_cm.py \
  --cmts-hostname "${CMTS_HOST}" \
  --cmts-community "${SNMP_COMMUNITY}"
```

Fetch CM registration entries for a specific serving group:

```bash
CMTS_HOST="192.168.0.100"
SNMP_COMMUNITY="public"
SERVING_GROUP_ID=7

python src/pypnm_cmts/examples/cli/get_all_registered_cm.py \
  --cmts-hostname "${CMTS_HOST}" \
  --cmts-community "${SNMP_COMMUNITY}" \
  --serving-group-id "${SERVING_GROUP_ID}"
```

## Get registered CM MAC + IP tuples (SNMPv2c)

Fetch CM MAC and IP address tuples for a serving group (default JSON output).

```bash
CMTS_HOST="192.168.0.100"
SNMP_COMMUNITY="public"
SERVING_GROUP_ID=7

python src/pypnm_cmts/examples/cli/get_all_registered_cm_mac_inet.py \
  --cmts-hostname "${CMTS_HOST}" \
  --cmts-community "${SNMP_COMMUNITY}" \
  --serving-group-id "${SERVING_GROUP_ID}"
```

Fetch CM MAC and IP address tuples for all serving groups:

```bash
CMTS_HOST="192.168.0.100"
SNMP_COMMUNITY="public"

python src/pypnm_cmts/examples/cli/get_all_registered_cm_mac_inet.py \
  --cmts-hostname "${CMTS_HOST}" \
  --cmts-community "${SNMP_COMMUNITY}"
```

## Get CM inet addresses by MAC (SNMPv2c)

Fetch CM inet addresses for a specific MAC address (default JSON output).

```bash
CMTS_HOST="192.168.0.100"
SNMP_COMMUNITY="public"
CM_MAC="aa:bb:cc:dd:ee:ff"

python src/pypnm_cmts/examples/cli/get_cm_inet_address.py \
  --cmts-hostname "${CMTS_HOST}" \
  --cmts-community "${SNMP_COMMUNITY}" \
  --mac "${CM_MAC}"
```

Fetch CM inet addresses with raw SNMP values:

```bash
CMTS_HOST="192.168.0.100"
SNMP_COMMUNITY="public"
CM_MAC="aa:bb:cc:dd:ee:ff"

python src/pypnm_cmts/examples/cli/get_cm_inet_address.py \
  --cmts-hostname "${CMTS_HOST}" \
  --cmts-community "${SNMP_COMMUNITY}" \
  --mac "${CM_MAC}" \
  --raw
```

## Next steps

- Update the Python API docs when new parsers or data models are added.
- Update the FastAPI docs when endpoints are introduced.

## Orchestrator run modes (Phase-0 wiring)

Standalone mode:

```bash
pypnm-cmts run --mode standalone
```

Controller mode:

```bash
pypnm-cmts run --mode controller
```

Worker mode (requires service group id):

```bash
pypnm-cmts run --mode worker --sg-id sg-001
```
