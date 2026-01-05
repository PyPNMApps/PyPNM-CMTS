# CMTS Request Schema

## Assumptions

- Most operations assume all cable modems (CMs) within a CMTS can share the same TFTP and SNMP settings.
- TFTP and SNMP defaults are configured at install time (or container deployment time).
- Defaults come from the inherited PyPNM `system.json` configuration (PyPNM-CMTS inherits PyPNM settings).
- CLI overrides may be provided at runtime (examples):
  - `--cm-snmpv2c-write-community`
  - `--cm-tftp-ipv4`
  - `--cm-tftp-ipv6`

## Selection Semantics (Important)

### Service Group Scope

- `cmts.serving_group.id` is a list of service-group identifiers.
- An empty list means **all serving groups**, unless an endpoint explicitly defines different behavior.
- Endpoints may further constrain scope (for example, only allowing a single SG per request); those constraints must be documented per endpoint.

### Cable Modem Scope

- `cmts.cable_modem.mac_address` is a list of CM MAC addresses.
- An empty list means **all cable modems** in the request’s effective scope (for example, in the selected serving group set), unless an endpoint explicitly defines different behavior.

Notes:
- Some endpoints may require an explicit non-empty list (for safety or performance). When that is the case, the endpoint documentation must say so explicitly.
- If an endpoint’s API documentation is silent, treat an empty list as “apply to all” for that field.

## Schema: Basic Serving Group Filter

Field:
- `cmts.serving_group.id`: list[int]

Meaning:
- `[]` applies to all serving groups unless overridden by the endpoint contract.

```json
{
  "cmts": {
    "serving_group": {
      "id": [3147266, 3213825]
    }
  }
}
```

“All SGs” example:

```json
{
  "cmts": {
    "serving_group": {
      "id": []
    }
  }
}
```

## Schema: Cable Modem Request (PNM Operation)

Required:
- `cmts.cable_modem.mac_address`: list[str]

Optional (defaults from `system.json` if omitted):
- `cmts.cable_modem.pnm_parameters.tftp.ipv4`: string
- `cmts.cable_modem.pnm_parameters.tftp.ipv6`: string
- `cmts.cable_modem.snmp.snmpV2C.community`: string

Assumptions:
- TFTP servers and SNMP community are the same for all CMs in-scope unless overridden in the request.

```json
{
  "cmts": {
    "cable_modem": {
      "mac_address": ["aa:bb:cc:dd:ee:ff"],
      "pnm_parameters": {
        "tftp": {
          "ipv4": "192.168.0.10",
          "ipv6": "2001:db8::10"
        }
      },
      "snmp": {
        "snmpV2C": {
          "community": "private"
        }
      }
    }
  }
}
```

“All CMs” example (applies to all cable modems in the effective scope unless the endpoint says otherwise):

```json
{
  "cmts": {
    "cable_modem": {
      "mac_address": [],
      "pnm_parameters": {
        "tftp": {
          "ipv4": "192.168.0.10",
          "ipv6": "2001:db8::10"
        }
      },
      "snmp": {
        "snmpV2C": {
          "community": "private"
        }
      }
    }
  }
}
```

## Schema: Cable Modem Request (Non-PNM Operation)

Required:
- `cmts.cable_modem.mac_address`: list[str]

Optional (defaults from `system.json` if omitted):
- `cmts.cable_modem.snmp.snmpV2C.community`: string

Assumptions:
- SNMP community is the same for all CMs in-scope unless overridden in the request.

```json
{
  "cmts": {
    "cable_modem": {
      "mac_address": ["aa:bb:cc:dd:ee:ff"],
      "snmp": {
        "snmpV2C": {
          "community": "private"
        }
      }
    }
  }
}
```

“All CMs” example (applies to all cable modems in the effective scope unless the endpoint says otherwise):

```json
{
  "cmts": {
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

## Codex Primer (Implementation Notes)

Goal: Align endpoint request parsing and validators with the following rules:

- `cmts.serving_group.id == []` means “all serving groups” unless the endpoint explicitly overrides this behavior.
- `cmts.cable_modem.mac_address == []` means “all cable modems in the effective scope” unless the endpoint explicitly overrides this behavior.
- Endpoints that do not support “all” semantics must document that exception and enforce it via validation.

Recommended implementation pattern:

- Normalize selection lists early (request model validation or request handler pre-processing).
- When empty means “all,” resolve the actual set using the SGW cache/discovery snapshot rather than triggering implicit SNMP walks.
- For endpoints with potentially expensive operations, prefer:
  - explicit allow-list (reject empty list), or
  - a separate boolean flag (for example `apply_to_all: true`) if you want to force explicit user intent.
  If you choose this path, the endpoint must document the override clearly.
