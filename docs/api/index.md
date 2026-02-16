# API reference

Start here for CMTS API references, including FastAPI endpoints and Python helpers.

## Sections

- [FastAPI endpoints](fast-api/index.md)
- [Python API](python/index.md)

## Endpoint groups

- [Operational endpoints](fast-api/operational.md)
  - Health, readiness, version, process status, and SGW worker runtime controls.
- [Serving group endpoints](fast-api/serving-group.md)
  - Serving-group discovery, cached cable modem inventory, topology, and modem operations.
- [SG PNM operations](fast-api/pnm-sg-operations.md)
  - PNM operation lifecycle endpoints grouped by operation family.
- [RxMER deep dive](fast-api/pnm-rxmer.md)
  - Detailed request/response and lifecycle semantics for RxMER orchestration.
- [SG operations data model](fast-api/pypnm-cmts/sg-operations.md)
  - Storage and traceability model behind SG PNM operation responses.

## Suggested reading order

1. [FastAPI endpoints](fast-api/index.md)
2. [Serving group endpoints](fast-api/serving-group.md)
3. [SG PNM operations](fast-api/pnm-sg-operations.md)
4. [SG operations data model](fast-api/pypnm-cmts/sg-operations.md)
