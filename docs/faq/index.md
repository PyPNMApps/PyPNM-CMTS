# FAQ

## Why does `pypnm-cmts serve` exit with "adapter.hostname must be set for snmp discovery"?

PyPNM-CMTS defaults to SNMP discovery mode. In this mode the service must know the CMTS
hostname or IP address, along with SNMP credentials, before startup can complete.

Resolution options:

1) Run with CLI overrides for one-off startup:

```bash
pypnm-cmts serve --cmts-hostname 192.168.0.100 --read-community public --write-community public
```

2) Initialize and persist configuration:

```bash
pypnm-cmts config init
pypnm-cmts config-menu
pypnm-cmts config validate
pypnm-cmts serve
```

You can also preflight your configuration without starting the service:

```bash
pypnm-cmts config validate
```

## Why does `/cm/docs/pnm/ds/ofdm/rxMer/getCapture` return 422 for blank TFTP or SNMP fields?

PyPNM requires the override fields to be present in the request body, but blank strings are invalid.
Use `null` to request system.json defaults for:

- `cable_modem.pnm_parameters.tftp.ipv4`
- `cable_modem.pnm_parameters.tftp.ipv6`
- `cable_modem.snmp.snmpV2C.community`

Resolution:

1) Send explicit values for the overrides, or send `null` to use system.json defaults.
2) Do not send empty strings for these fields.
3) If `tftp` or `snmpV2C` objects are provided, their keys must be present (use `null` for defaults).
4) Duplicate list entries in request filters are rejected (for example, repeated `serving_group.id` values).
