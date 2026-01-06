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
