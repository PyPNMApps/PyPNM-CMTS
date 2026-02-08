# CODING_AGENTS.md

## Commit Message Output Style

- Always format requested commit messages as multi-line text.
- First line is the summary/title.
- Follow with detail lines prefixed by `- `.
- Keep each detail on its own line.
- Do not include double quotes, single quotes, or backticks in commit message output.

Example:

```text
Fix RxMER SNMP transport lifecycle between precheck and capture
- Build separate CableModem instances for precheck and capture
- Add CableModem factory helper in RxMER worker
- Add regression test for distinct precheck/capture CableModem instances
```

## CaptureWorker Rule

- Keep CaptureWorker classes lean.
- CaptureWorker classes should focus on the PNM operation flow only.
- Move shared back-and-forth behavior to common utilities or base services.
- Do not embed generic transport, parsing, and cross-operation lifecycle mechanics directly in endpoint-specific CaptureWorker classes.

## PyPNM Reuse Rule

- Reuse existing PyPNM constants before adding new local constants.
- Reuse PyPNM MacAddress, Inet, and shared PyPNM types before defining CMTS-local equivalents.
- Prefer PyPNM utility functions for shared parsing, normalization, and conversion behavior.
- Introduce CMTS-local constants or types only when no PyPNM equivalent exists, and record the rationale in the change notes.

## Typed Collections Rule

- Do not introduce raw generic integer collections like list[int] in production source.
- Use named aliases from pypnm_cmts lib types for integer collections and optional integer collections.
- When a needed alias does not exist in pypnm_cmts lib types, add it there first, then use the alias.

## PNM Data Type Placement Rule

- Place all PNM SNMP table data type models under `src/pypnm_cmts/pnm/data_type`.
- Do not place PNM SNMP table data type models under `src/pypnm_cmts/docsis/data_type`.

## CMTS Operation CLI Rule

- When a new SNMP table `get` or `set` entry method is added to `src/pypnm_cmts/docsis/cmts_operation.py`, add a corresponding CLI example under `src/pypnm_cmts/examples/cli` in the same change.
- The CLI example must include JSON output support.
- Any CLI example that supports JSON output must provide a `--json-pretty` flag to format JSON with indentation.

## Private Method Placement Rule

- Except Python special methods (for example `__init__`), place private methods at the bottom of the class.
- This applies to methods prefixed with `_`, `__`, or more leading underscores.
- Methods with three or more leading underscores (for example `___helper`) must include a docstring that states they are internal-only and must not be used outside the class.
