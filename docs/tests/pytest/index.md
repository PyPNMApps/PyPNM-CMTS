# Pytest Guide

This guide summarizes how to run PyPNM-CMTS tests locally.

## Quick Commands

Run the full test suite:

```bash
pytest -q
```

Run only the serving-group endpoint contract tests:

```bash
pytest -q tests/test_sgw_endpoints.py
```

Run integration tests (opt-in):

```bash
pytest -q -m integration
```

Run integration tests marked slow:

```bash
pytest -q -m "integration and slow"
```

## Live CMTS Tests

Live CMTS integration tests are opt-in and are skipped unless the required
environment variables are set. See `docs/tests/pytest/live-cmts.md` for details.
