# Step Review Packet

## Repo + Branch + HEAD

- Repo: /home/dev01/Projects/PyPNM-CMTS
- Branch: Phase10-Refactor-System-Default
- HEAD: 92fcdaf

## Staged File List

```text
M	README.md
M	docs/api/fast-api/index.md
A	docs/api/fast-api/pnm-rxmer.md
M	docs/architecture/schema/cmts-request.md
M	docs/faq/index.md
A	docs/planning/phase10.md
M	docs/todo/todo.md
M	pyproject.toml
M	src/pypnm_cmts/api/common/cmts/schema.py
M	src/pypnm_cmts/api/common/cmts_request.py
A	src/pypnm_cmts/api/common/service/pnm/__init__.py
A	src/pypnm_cmts/api/common/service/pnm/executor.py
A	src/pypnm_cmts/api/common/validation/__init__.py
A	src/pypnm_cmts/api/common/validation/request_normalization.py
M	src/pypnm_cmts/api/routes/operational/router.py
M	src/pypnm_cmts/api/routes/orchestrator/router.py
A	src/pypnm_cmts/api/routes/pnm/__init__.py
A	src/pypnm_cmts/api/routes/pnm/router.py
A	src/pypnm_cmts/api/routes/pnm/rxmer/__init__.py
A	src/pypnm_cmts/api/routes/pnm/rxmer/router.py
A	src/pypnm_cmts/api/routes/pnm/rxmer/schemas.py
A	src/pypnm_cmts/api/routes/pnm/rxmer/service.py
M	src/pypnm_cmts/api/routes/serving_group/router.py
M	src/pypnm_cmts/api/routes/system/router.py
M	src/pypnm_cmts/api/utils/auto_load.py
A	src/pypnm_cmts/api/utils/fastapi_responses.py
M	src/pypnm_cmts/lib/constants.py
M	tests/test_cmts_request_models.py
M	tests/test_pypnm_docsis_version.py
A	tests/test_rxmer_orchestration.py
A	tools/review/step-review.md
```

## Staged Diffstat

```text
 README.md                                          |   10 +-
 docs/api/fast-api/index.md                         |    4 +
 docs/api/fast-api/pnm-rxmer.md                     |  106 ++
 docs/architecture/schema/cmts-request.md           |    7 +-
 docs/faq/index.md                                  |   16 +
 docs/planning/phase10.md                           |   73 ++
 docs/todo/todo.md                                  |    1 +
 pyproject.toml                                     |    2 +-
 src/pypnm_cmts/api/common/cmts/schema.py           |    2 +-
 src/pypnm_cmts/api/common/cmts_request.py          |   95 +-
 src/pypnm_cmts/api/common/service/pnm/__init__.py  |   26 +
 src/pypnm_cmts/api/common/service/pnm/executor.py  |  332 +++++
 src/pypnm_cmts/api/common/validation/__init__.py   |    8 +
 .../api/common/validation/request_normalization.py |  161 +++
 src/pypnm_cmts/api/routes/operational/router.py    |    9 +
 src/pypnm_cmts/api/routes/orchestrator/router.py   |    5 +-
 src/pypnm_cmts/api/routes/pnm/__init__.py          |   10 +
 src/pypnm_cmts/api/routes/pnm/router.py            |   11 +
 src/pypnm_cmts/api/routes/pnm/rxmer/__init__.py    |   11 +
 src/pypnm_cmts/api/routes/pnm/rxmer/router.py      |   62 +
 src/pypnm_cmts/api/routes/pnm/rxmer/schemas.py     |  125 ++
 src/pypnm_cmts/api/routes/pnm/rxmer/service.py     |  515 ++++++++
 src/pypnm_cmts/api/routes/serving_group/router.py  |    5 +
 src/pypnm_cmts/api/routes/system/router.py         |    4 +-
 src/pypnm_cmts/api/utils/auto_load.py              |    4 +-
 src/pypnm_cmts/api/utils/fastapi_responses.py      |   31 +
 src/pypnm_cmts/lib/constants.py                    |   17 +
 tests/test_cmts_request_models.py                  |  101 +-
 tests/test_pypnm_docsis_version.py                 |   23 +-
 tests/test_rxmer_orchestration.py                  |  434 +++++++
 tools/review/step-review.md                        | 1355 ++++++++++++++++++++
```

## Findings

### Confirmed behaviors

- Duplicate list entries are rejected for serving_group.id, cable_modem.mac_address, and pnm_parameters.capture.channel_ids via RequestListNormalizer.assert_unique_* (src/pypnm_cmts/api/common/cmts_request.py:24, src/pypnm_cmts/api/common/validation/request_normalization.py:28).
- TFTP/SNMP override rules enforce keys present, null accepted, blank rejected (src/pypnm_cmts/api/common/cmts_request.py:36, src/pypnm_cmts/api/common/cmts_request.py:74).
- RxMER orchestration forwards channel_ids in order and uses bounded retries and timeouts via PnmCaptureExecutor (src/pypnm_cmts/api/routes/pnm/rxmer/service.py:148, src/pypnm_cmts/api/common/service/pnm/executor.py:111).
- In-flight dedupe returns already_running with run_id, and run_id is reused for the in-flight request (src/pypnm_cmts/api/routes/pnm/rxmer/service.py:96).
- Router is mounted under /cmts/pnm/rxmer and uses JSON-only FAST_API_RESPONSE (src/pypnm_cmts/api/routes/pnm/rxmer/router.py:20).

### Risks / potential bugs

- Summary requested_count uses total snapshot modem count even when request filters by cmts.cable_modem.mac_address, so requested_count/total_modems can exceed the requested scope (src/pypnm_cmts/api/routes/pnm/rxmer/service.py:165-173).
- In-flight dedupe key is order-sensitive for channel_ids, so [1,2] and [2,1] are treated as different runs even though they likely target the same channel set (src/pypnm_cmts/api/routes/pnm/rxmer/service.py:416-421).

### Doc/API inconsistencies

- Response example shows "ipv6": "" but responses serialize ipv6 as null when empty, so the example does not match runtime output (docs/api/fast-api/pnm-rxmer.md:80-82).

### Required fixes

- Update requested_count/total_modems semantics (or labels) to reflect filtered MAC requests, or document that requested_count always reflects full SG snapshot (src/pypnm_cmts/api/routes/pnm/rxmer/service.py:165-173).
- Align the RxMER response example ipv6 field with actual output (docs/api/fast-api/pnm-rxmer.md:80-82).

## Ready to Commit?

NO — summary count semantics and the response example mismatch should be resolved before commit.
