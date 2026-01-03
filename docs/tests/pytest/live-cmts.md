# Live CMTS Integration Tests

This document explains how to run the opt-in live CMTS integration tests.
These tests validate API contracts against a real CMTS and are not required
for typical development runs.

## Required Environment Variables

Set the following environment variables before running live tests:

- `PYPNM_CMTS_LIVE=1`
- `CMTS_HOSTNAME` (example: `192.168.0.100`)
- `CMTS_SNMP_V2_COMMUNITY` (example: `public`)

## Example Commands

```bash
export PYPNM_CMTS_LIVE=1
export CMTS_HOSTNAME=192.168.0.100
export CMTS_SNMP_V2_COMMUNITY=public

pytest -q -m integration
```

## Reachability Checks

The live test suite checks host reachability before running:

1) `ping -c 1 -W 1 <host>` on Linux
2) If ping is unavailable or fails, a short TCP connect check against common
   ports (22, 80)

If the host is unreachable, the tests are skipped with a clear message.

## What To Expect

- Cache-first SGW endpoints may return empty cable modem lists or topology
  entries if SGW pollers are not yet wired to populate cache entries.
- System endpoints (`/system/sysDescr` and `/system/serviceGroupTopology`)
  should return non-empty results when the CMTS is reachable.
