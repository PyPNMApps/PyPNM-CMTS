# API Common Status Codes

PyPNM-CMTS keeps a shared status code contract with PyPNM FastAPI responses.

## Why two enums exist

- ServiceStatusCode (PyPNM) is the shared/common enum used by both projects.
- CmtsStatusCode (PyPNM-CMTS) is for CMTS-only codes that must not collide with PyPNM.

## Reserved ranges

- PyPNM reserved range: <= 9999
- PyPNM-CMTS reserved range: >= 10000
- Do not renumber or reuse PyPNM codes.

## Interpreting codes

- ServiceStatusCode values map to PyPNM-defined outcomes.
- CmtsStatusCode values are CMTS-only and must use the reserved range.
- If a response uses CMTS-only codes, the caller should treat the value as
  PyPNM-CMTS-specific.

Download: [api/common/index.md](index.md)
