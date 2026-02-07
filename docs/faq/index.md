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

## Why can a successful RxMER capture appear as `FAILED` with missing transaction id?

This can happen when capture payload parsing expects raw dictionaries while PyPNM returns typed payload entries.
In that case, transaction metadata is not extracted even though capture succeeded, and the operation may be marked
as failed with a missing transaction id message.

Resolution:

1) Update RxMER payload parsing to handle PyPNM `MessagePayload` entries.
2) Validate that `PNM_FILE_TRANSACTION` entries produce both `transaction_id` and `filename`.
3) Re-run the capture and confirm status transitions to `COMPLETED` when capture succeeds.
