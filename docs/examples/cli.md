# CLI examples

Use these examples to fetch CMTS sysDescr data via SNMP.

## Get sysDescr (SNMPv2c)

Fetch the CMTS `sysDescr` via SNMPv2c. The command exits with code `1` when the
response is empty or the request fails.

### Linux/macOS

```bash
CMTS_HOST="172.19.124.6"
SNMP_COMMUNITY="cmtspublic"
SNMP_PORT=161

python example/cli/get_sysdescr.py "${CMTS_HOST}" -c "${SNMP_COMMUNITY}" -p "${SNMP_PORT}"
```

JSON output:

```bash
CMTS_HOST="172.19.124.6"
SNMP_COMMUNITY="cmtspublic"

python example/cli/get_sysdescr.py "${CMTS_HOST}" -c "${SNMP_COMMUNITY}" --json
```

### Windows PowerShell

```powershell
$env:CMTS_HOST = "172.19.124.6"
$env:SNMP_COMMUNITY = "cmtspublic"
$env:SNMP_PORT = "161"

python example/cli/get_sysdescr.py $env:CMTS_HOST -c $env:SNMP_COMMUNITY -p $env:SNMP_PORT
```

JSON output:

```powershell
$env:CMTS_HOST = "172.19.124.6"
$env:SNMP_COMMUNITY = "cmtspublic"

python example/cli/get_sysdescr.py $env:CMTS_HOST -c $env:SNMP_COMMUNITY --json
```

### Output

- Text: `Cisco IOS Software [IOSXE], cBR Software (...)`
- JSON: `{"vendor":"Cisco","platform":"cBR Software (X86_64_LINUX_IOSD-UNIVERSALK9-M)","software":"IOSXE","version":"17.15.1z","release":"fc3",...}`

## Next steps

- Update the Python API docs when new parsers or data models are added.
- Update the FastAPI docs when endpoints are introduced.
