# CODING_AGENTS.md

This document defines coding guidance for AI contributors in PyPNM-CMTS.
It complements AGENTS.md and does not replace it.

## Core Principles

- Reuse before adding new code.
- Keep diffs minimal and focused.
- Preserve existing naming, spacing, and alignment patterns.
- Favor explicit typing and clear behavior over clever shortcuts.
- Avoid broad refactors unless explicitly requested.

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
- Add regression test for distinct precheck and capture CableModem instances
```

## Reuse-First Checklist

Before introducing new types, constants, validators, or storage patterns:

- Check `src/pypnm_cmts/lib/types.py` for an existing alias.
- Check `src/pypnm_cmts/lib/constants.py` for an existing constant.
- Check `src/pypnm_cmts/api/common/` for existing shared models and helpers.
- Check PyPNM equivalents in `/home/dev01/Projects/PyPNM/src/pypnm/` and reuse when suitable.
- Prefer existing Pydantic models for public payloads over raw dictionaries.

## PyPNM Reuse Rule

- Reuse existing PyPNM constants before adding new local constants.
- Reuse PyPNM MacAddress, Inet, and shared PyPNM types before defining CMTS-local equivalents.
- Prefer PyPNM utility functions for shared parsing, normalization, and conversion behavior.
- Introduce CMTS-local constants or types only when no PyPNM equivalent exists, and record the rationale in change notes.

## CaptureWorker Rule

- Keep CaptureWorker classes lean.
- CaptureWorker classes should focus on the PNM operation flow only.
- Move shared back-and-forth behavior to common utilities or base services.
- Do not embed generic transport, parsing, and cross-operation lifecycle mechanics directly in endpoint-specific CaptureWorker classes.

## Typing And API Style

- Use built-in generics like `list[str]` and unions like `A | B`.
- Avoid `Any` unless unavoidable and clearly justified.
- Annotate all function arguments and return types.
- Prefer Pydantic `BaseModel` for public interfaces instead of raw dict payloads.
- Use shared public aliases from `src/pypnm_cmts/lib/types.py`.
- Define local aliases only when strictly private and not reused.
- Avoid generic dict arguments for public method contracts; prefer typed models.

## Typed Collections Rule

- Do not introduce raw generic integer collections like `list[int]` in production source.
- Use named aliases from `pypnm_cmts` lib types for integer collections and optional integer collections.
- When a needed alias does not exist in `pypnm_cmts` lib types, add it there first, then use the alias.

## Class And Method Structure

- Except Python special methods (for example `__init__`), place private methods at the bottom of the class.
- This applies to methods prefixed with `_`, `__`, or more leading underscores.
- Methods with three or more leading underscores (for example `___helper`) must include a docstring that states they are internal-only and must not be used outside the class.
- Public methods should have detailed docstrings; private methods should have concise docstrings.

## Import Style Rule

- Use absolute package imports in source files.
- Do not use relative imports such as `from .module import ...`.

## Logger Naming Rule

- Do not use full module-path logger names in production classes.
- Avoid `logging.getLogger(__name__)` in class-based service/router/runtime modules.
- Use class-name loggers for class-based components, for example `logging.getLogger(self.__class__.__name__)`.

## Markdown SysDescr Example Rule

- For Markdown documentation examples that include sysDescr payloads, use LANCity as the example vendor and model naming.

## Logging Format Rule

- Use class-name logger names in production classes.
- Keep operation labels in CaseSnake inside brackets for all log operations, for example `[REFRESH_HEAVY]` and `[CM_SYSDESCR_RESULT]`.
- Use clear operation names with consistent casing in log messages.
- Log only required troubleshooting context fields (for example `sg_id`, `mac`, `ip`, `community`) and avoid redundant keys.
- Do not expose SNMP community values in INFO, WARNING, or ERROR logs.
- SNMP community values may appear only at DEBUG level, using inline conditional formatting in a single log call.

## PNM Data Type Placement Rule

- Place all PNM SNMP table data type models under `src/pypnm_cmts/pnm/data_type`.
- Do not place PNM SNMP table data type models under `src/pypnm_cmts/docsis/data_type`.

## CMTS Operation CLI Rule

- When a new SNMP table `get` or `set` entry method is added to `src/pypnm_cmts/docsis/cmts_operation.py`, add a corresponding CLI example under `src/pypnm_cmts/examples/cli` in the same change.
- The CLI example must include JSON output support.
- Any CLI example that supports JSON output must provide a `--json-pretty` flag to format JSON with indentation.
- For set-operation CLI examples, use `--cmts-community-write` for the write community argument.

## Testing Expectations

- For code changes, run `ruff check src` and `pytest -q`.
- For Markdown-only changes, run `mkdocs build -s`.
- Add focused tests for new behavior and keep tests hermetic when possible.
- Reuse existing test patterns from similar modules before introducing new structures.
- Use `monkeypatch` only in tests.
- Do not use `monkeypatch` in production modules, runtime code paths, tools, or scripts.
- This applies to both `PyPNM-CMTS` and `PyPNM`.

## Repo Hygiene

- Use SPDX headers in code files where required by repository conventions.
- Do not add SPDX headers to Markdown files.
- Avoid formatting churn unrelated to the requested change.
