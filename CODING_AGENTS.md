# CODING_AGENTS.md

This document defines coding guidance for AI contributors in PyPNM-CMTS.
It complements AGENTS.md and does not replace it.

## Core Principles

- Reuse before adding new code.
- Keep diffs minimal and focused.
- Preserve existing naming, spacing, and alignment patterns.
- Favor explicit typing and clear behavior over clever shortcuts.
- Avoid broad refactors unless explicitly requested.
- Read `README.md` before making non-trivial changes.
- Do not auto-format unless the user explicitly requests formatting.

## Workflow Guardrails

- Preserve whitespace/alignment in touched files; avoid formatting churn.
- Keep changes scoped to the request; do not refactor unrelated modules.
- Prefer extending existing patterns and shared modules over creating new patterns.
- Use strict typing in production code and avoid generic container imports like `Dict`, `List`, `Tuple`, and `Union`.
- Avoid `Any` unless unavoidable and explicitly justified.
- Prefer `match/case` over long if/else chains.
- No code should contain 3+ nested loops. 2 nested loops are discouraged unless necessary.

## Configuration

- `system.json` is the single source of truth.
- New configuration namespaces must be implemented as Pydantic BaseModels.
- BaseModels must use one-line `Field(..., description="...")`.
- Avoid generic `str` for semantic identifiers or paths in public models and APIs; use an existing semantic type or add a new alias in `src/pypnm/lib/types.py`.
- When working with MAC or inet strings, validate using `MacAddress()` or `Inet()` instead of assuming `str(...)` formatting is valid.
- Request override defaults: missing or null means use `system.json` defaults; blank strings are invalid.

## Timestamp Conventions

- All stored timestamps are epoch seconds.
- Convert to ISO-8601 only at display or external response boundaries.

## Default Ports

- PyPNM-CMTS FastAPI default port is `8080`.
- PyPNM-CMTS MkDocs default local docs port is `8081`.
- When updating scripts, docs, examples, aliases, or smoke helpers, treat `8080` and `8081` as the defaults unless the user explicitly asks otherwise.

## Commit Message Output Style

- If request via chat request starts with commit-msg, then preface command ./tools/git/git-save.sh with commit-msg "<commit-msg>"
- One line summary (max 50 characters)
- One line Summary start: Feature: , Bugfix: , Docs: , Refactor: , Test:
- Detailed description lines (max 72 characters per line); every line after the first must start with `-`
- When the user asks for a commit message, provide plain text for direct paste into the terminal or UI text box.
- Do not wrap commit message suggestions in quotes (`"`), backticks (`` ` ``), or code fences unless the user explicitly asks for that format.
- Prefer detailed commit messages that describe the current change set clearly.
- Do not default to a one-line commit message when the change set is broad; provide a title plus concise bullet points.
- Avoid redundant wording and avoid repeating the exact prior commit message suggestion unless the diff is unchanged and the user explicitly asks to reuse it.
- If the user asks for "in a text box", return plain text only (no markdown fence).
- If the user asks for "in a markdown text box", return the commit message inside a fenced code block with `text`.

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
- Check PyPNM equivalents in the active virtualenv install first (for example `./.env/lib/python*/site-packages/pypnm/`) and reuse when suitable.
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

## FastAPI Guidelines (PyPNM)

- Router files must be lean:
  - `router.py` contains routing glue only (APIRouter configuration, endpoint registration, HTTP status translation).
  - No business logic in `router.py`. Business logic must live in `service.py` for that route group (same folder) or a shared service module if reused.
- All request/response bodies must be Pydantic BaseModels.
- Prefer POST for payload submission and endpoint contracts (PyPNM default).
  - Allow GET only where already present or clearly appropriate (health, readiness, version, status).
- Reuse shared models under the existing `src/pypnm_cmts/api/common/` structure (inspect current tree before adding anything new).
- Do not block request paths with `time.sleep()`.

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
- For substantial code changes, also run `python3 -m compileall src` and `ruff format --check .`.
- For Markdown-only changes, run `mkdocs build -s`.
- Add focused tests for new behavior and keep tests hermetic when possible.
- Reuse existing test patterns from similar modules before introducing new structures.
- Use `monkeypatch` only in tests.
- Do not use `monkeypatch` in production modules, runtime code paths, tools, or scripts.
- This applies to both `PyPNM-CMTS` and `PyPNM`.

## Tests (Mandatory)

- Every phase deliverable MUST include pytest coverage for new or changed behavior.
- Do not claim a phase item is complete unless pytest has been added and executed (or a concrete blocker is documented).
- Tests must remain hermetic: no live CMTS/cable modem dependencies.

## Documentation Guardrails

- Keep Markdown compatible with both MkDocs and GitHub rendering.
- Use LANCity for sysDescr examples in Markdown.
- Use consistent placeholders in docs examples:
  - MAC: `aa:bb:cc:dd:ee:ff`
  - IP: `192.168.0.100`
  - system_description JSON: `{"HW_REV":"1.0","VENDOR":"LANCity","BOOTR":"NONE","SW_REV":"1.0.0","MODEL":"LCPET-3"}`

## Repo Hygiene

- Use SPDX headers in code files where required by repository conventions.
- Do not add SPDX headers to Markdown files.
- Avoid formatting churn unrelated to the requested change.

## Agent Self-Checks

Before responding:

- Re-read this file and `README.md`.
- Confirm pytest coverage exists or is explicitly blocked.
- Confirm pytest and ruff output have no deprecation warnings (treat as failures).
- Confirm changes align to the current phase and do not leak scope.
- Confirm formatting and alignment are preserved.

## Training

When the user requests "train", read the following sources:

- `AGENTS.md`
- `src/pypnm/lib/` (DB/persistence + config helpers)
- `src/pypnm/api/` (routing/service patterns, where applicable)
- `src/pypnm_cmts/lib/` (DB/persistence + config helpers)
- `src/pypnm_cmts/api/` (routing/service patterns, where applicable)
- `tools/agent-review/` (all files, if present)
