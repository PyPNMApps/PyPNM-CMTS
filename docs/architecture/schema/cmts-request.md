# CMTS Request Schema Contract

## Assumptions

- Most operations assume all cable modems (CMs) within a CMTS can share the same TFTP and SNMP settings.
- TFTP and SNMP defaults are configured at install time (or container deployment time).
- Defaults come from the inherited PyPNM `system.json` configuration (PyPNM-CMTS inherits PyPNM settings).

## Canonical Request Envelope

All CMTS-backed endpoints accept a single top-level `cmts` object. The fields under `cmts` are shared across endpoints and must be interpreted consistently unless a specific endpoint explicitly states a constraint.

### Service Group Scope

- `cmts.serving_group.id` is a list of service-group identifiers (integers).
- An empty list or missing field means **all serving groups**, unless an endpoint explicitly requires a service-group filter.
- Endpoints may further constrain scope (for example, only allowing a single SG per request); those constraints must be documented per endpoint.

### Cable Modem Scope

- `cmts.cable_modem.mac_address` is a list of CM MAC addresses (strings).
- An empty list or missing field means **all cable modems** in the effective scope, unless an endpoint explicitly requires explicit MACs.

## PNM vs Non-PNM Operations

### PNM Operations

- PNM endpoints may accept optional overrides for TFTP and SNMP write community per request.
- TFTP and SNMP values apply to all cable modems in-scope for the request.
- `cmts.cable_modem.pnm_parameters.capture.channel_ids` optionally filters downstream channels for capture operations; empty or missing means all channels.

### Non-PNM Operations

- Non-PNM endpoints typically use SNMP only and ignore TFTP fields.
- SNMP write community overrides are optional and apply to all cable modems in-scope.

## CLI Overrides

The CLI supports optional CM-side override parameters that map directly to the request schema fields. Precedence is:

1) CLI overrides
2) Request body overrides (if the endpoint explicitly allows them)
3) `system.json` defaults

Planned flags:
- `--cm-snmpv2c-write-community`
- `--cm-tftp-ipv4`
- `--cm-tftp-ipv6`

## Endpoint Overrides

Endpoint pages may require explicit serving-group filters or explicit MAC lists. When that is the case, the endpoint documentation must state the exception and the endpoint must validate accordingly.

## Cable Modem Registration Status (Response)

When endpoints return cable modem registration state, they use the canonical object shape:

```json
{
  "registration_status": {
    "status": 8,
    "text": "operational"
  }
}
```

Unknown numeric values map to `"text": "other"`.

## Examples

### Serving Group Filter Only (All Cable Modems)

```json
{
  "cmts": {
    "serving_group": {
      "id": [1001, 1002]
    }
  }
}
```

### Cable Modem Filter Only (All Serving Groups)

```json
{
  "cmts": {
    "cable_modem": {
      "mac_address": ["aa:bb:cc:dd:ee:ff"]
    }
  }
}
```

### Serving Group + Cable Modem Filters With Overrides

```json
{
  "cmts": {
    "serving_group": {
      "id": [1001]
    },
    "cable_modem": {
      "mac_address": ["aa:bb:cc:dd:ee:ff"],
      "pnm_parameters": {
        "tftp": {
          "ipv4": "192.168.0.100"
        },
        "capture": {
          "channel_ids": [193]
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
