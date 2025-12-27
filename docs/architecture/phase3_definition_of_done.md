## Phase-3 Definition Of Done Checklist (Before Tagging v0.1.6.0)

Phase 3 Closed: Orchestrator skeleton, CLI wiring, tests, and documentation updates are complete. The remaining items are non-gating doc cosmetics deferred to Phase 4.

### A. Architecture Scope Guardrails

* [x] No SNMP discovery logic added (no CMTS polling loops, no CM workflows, no provisioning).
* [x] No external coordination backend introduced (no Redis, no K8 APIs, no DB).
* [x] Orchestrator remains filesystem-only and deterministic.
* [x] Coordination primitives remain reusable/stateless (no "hidden" scheduler state inside coordination layer).

### B. Orchestrator Runtime (Long-Running)

* [x] A dedicated runtime class exists (e.g., `CmtsOrchestratorRuntime`) under `src/pypnm_cmts/orchestrator/`.
* [x] Runtime supports a deterministic tick loop:

  * [x] "Tick" calls `CoordinationManager.tick(...)` consistently.
  * [x] Runtime can stop cleanly (explicit stop path for tests; signal handling optional but acceptable).
* [x] `CmtsOrchestratorLauncher` supports:

  * [x] `run_once()` preserved (no regression to your Phase-0 single-tick contract).
  * [x] `run_forever()` added and used by CLI for long-running execution.

### C. Configuration Contract (Pydantic)

* [x] `CmtsOrchestratorSettings` includes launcher-owned coordination inputs (wired, not just documented):

  * [x] `state_dir`
  * [x] `election_name` (or prefix/label strategy, but the CLI and settings must expose a single consistent contract)
  * [x] `leader_ttl_seconds`
  * [x] `lease_ttl_seconds`
  * [x] `tick_interval_seconds`
* [x] Tick interval safety is enforced:

  * [x] `tick_interval_seconds < min(leader_ttl_seconds, lease_ttl_seconds)`
  * [x] Validation produces a clear error message.
* [x] Defaults are sane and conservative (no magic values sprinkled; use named constants).
* [x] Worker scaling remains by Service Group and is configurable (target SG count).

### D. CLI Wiring (Phase-3 Flags)

* [x] `pypnm-cmts run` exposes and wires the documented coordination flags:

  * [x] `--mode standalone|controller|worker`
  * [x] `--sg-id <int>` required when `--mode worker`
  * [x] `--owner-id <str>`
  * [x] `--target-service-groups <int>`
  * [x] `--shard-mode sequential|score`
  * [x] `--tick-interval-seconds <int|float>`
  * [x] `--leader-ttl-seconds <int>`
  * [x] `--lease-ttl-seconds <int>`
  * [x] `--state-dir <path>`
  * [x] `--election-name <str>`
* [x] CLI output contract:

  * [x] Each tick prints JSON (single-line JSON acceptable; structured model preferred).
  * [x] Emojis only appear in CLI output (allowed) and install.sh; nowhere else.

### E. Worker Scaling Emphasis (SG Workers)

* [x] The controller/standalone modes compute SG inventory deterministically from config.
* [x] Worker mode operates on exactly one SG (from `--sg-id`) and does not attempt global acquisition.
* [x] `target_service_groups` is clamped to inventory size (you already started this; keep it consistent).

### F. Documentation Updates (Minimal but Complete)

* [x] `docs/system/cli.md` updated to reflect actual CLI flags (no "planned" section for implemented flags).
* [x] `docs/examples/cli.md` updated with:

  * [x] New flags usage examples (clear-prefixed for bash; PowerShell uses Clear-Host).
  * [x] Run modes reflect whether it's single-tick or long-running (be explicit).
* [x] Docs remain MkDocs + GitHub compatible; no emojis in docs.

### G. Test Coverage (Mandatory)

* [x] Pytest coverage added for:

  * [x] tick interval validation (valid/invalid boundaries)
  * [x] runtime loop executes N ticks without sleeping (inject sleeper or loop counter)
  * [x] CLI parsing for new flags + invalid combinations return `EXIT_CODE_USAGE`
  * [x] worker `--sg-id` numeric requirement remains enforced
* [x] Tests do not require a real CMTS (mock coordination and/or use tmp_path filesystem).

### H. Quality Gates (Run And Pass)

Run exactly (prefixed with `clear` as you prefer):

```bash
clear && . .env/bin/activate && pytest -q
clear && . .env/bin/activate && ruff check . --no-cache
clear && . .env/bin/activate && mkdocs build --strict
```

### I. Release Hygiene

* [x] Changelog/release notes updated (whatever your repo uses).
* [x] Version bumped appropriately and tagged (v0.1.6.0).
* [x] No leftover "planned" flags in docs for things that are now real.
* [x] No policy regressions (emoji rules, typing rules, no magic numbers).

### Deferred (Non-gating, Phase 4 Backlog)

* Documentation cosmetic cleanup in CLI docs (duplicate phrasing, formatting polish).
