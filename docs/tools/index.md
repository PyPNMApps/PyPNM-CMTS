# Tools

Operational tools and helpers for PyPNM-CMTS.

## Maintenance

### tools/maintenance/clean.sh

Cleanup utility for logs, caches, build artifacts, and runtime data directories.

```bash
tools/maintenance/clean.sh --all
```

```bash
tools/maintenance/clean.sh --logs --python
```

Key options:
- `--all` full cleanup
- `--logs` truncate `logs/*.log`
- `--python` remove `__pycache__`, `.pytest_cache`, `.ruff_cache`, etc.
- `--build` remove `build/`, `dist/`, `*.egg-info`
- `--pnm`, `--archive`, `--excel`, `--json`, `--plot-data`, `--msg-rsp` clean specific `.data` paths
- `--issues`, `--remove-issues` clean or remove `issues/`
- `--settings-backup` remove `src/pypnm_cmts/settings/system.bak.*.json`

### tools/maintenance/add-required-python-headers.py

Ensures SPDX header, copyright line, and optional `from __future__ import annotations`.

```bash
tools/maintenance/add-required-python-headers.py .
```

```bash
tools/maintenance/add-required-python-headers.py . --future auto --author "Maurice Garcia" --year 2025
```

Options:
- `--exclude` comma-separated directory list
- `--future` `auto|yes|no`
- `--author`, `--year`
- `--verbose`

## Security

### tools/security/scan-mac-addresses.py

Scans the repo for non-approved MAC addresses. Respects `.gitignore` directories by default.

```bash
tools/security/scan-mac-addresses.py --fail-on-found
```

```bash
tools/security/scan-mac-addresses.py --fail-on-found --skip-gitignore
```

Options:
- `--root <path>` root directory (default current)
- `--fail-on-found` exit with status 2 if any non-approved MACs are found
- `--skip-gitignore` ignore `.gitignore` directory entries when scanning

### tools/security/scan-secrets.sh

Runs gitleaks (if installed) or a heuristic scan for secret-like strings.

```bash
tools/security/scan-secrets.sh
```

```bash
tools/security/scan-secrets.sh --all-history
```

Options:
- `--all-history` scan full git history (gitleaks only)
- `--path <dir>` override repo root

## Local

### tools/local/local_container_build.sh

Builds the local container and optionally runs a short docker-compose smoke test.

```bash
tools/local/local_container_build.sh
```

```bash
tools/local/local_container_build.sh --smoke
```

### tools/local/local_kubernetes_smoke.sh

Builds a local image and runs a Kubernetes smoke test against a local kind cluster.

```bash
tools/local/local_kubernetes_smoke.sh
```

## Release

### tools/release/release.py

Primary release helper (version bump, tests, tagging).

```bash
python tools/release/release.py --dry-run
```

```bash
python tools/release/release.py --next build
```

### tools/release/test-runner.py

Runs the release test sequence locally.

```bash
python tools/release/test-runner.py
```

### tools/release/check_version.py

Checks version consistency across project files.

```bash
python tools/release/check_version.py
```

## PNM

### tools/pnm/print_pypnm_cmts_system_json.py

Prints the PyPNM-CMTS system.json template.

```bash
python tools/pnm/print_pypnm_cmts_system_json.py
```

### tools/pnm/print_pypnm_docsis_system_json.py

Prints the PyPNM (pypnm-docsis) system.json template.

```bash
python tools/pnm/print_pypnm_docsis_system_json.py
```

## Support

### tools/support/bump_version.py

Updates version identifiers to a new release.

```bash
python tools/support/bump_version.py --version 0.2.0.0
```

## System Test

### tools/system-test/p4-coordination-harness.sh

Runs the Phase 4 coordination harness to validate controller/worker behavior.

```bash
tools/system-test/p4-coordination-harness.sh start --cmts-hostname 192.168.0.100 --read-community public --write-community public --state-dir ./.state/p4-demo --election-name p4-demo
```

```bash
tools/system-test/p4-coordination-harness.sh verify --state-dir ./.state/p4-demo --election-name p4-demo
```

```bash
tools/system-test/p4-coordination-harness.sh stop --state-dir ./.state/p4-demo
```

### tools/system-test/ops-smoke.sh

Checks that the FastAPI service is reachable by calling /ops/health.

```bash
tools/system-test/ops-smoke.sh --base-url http://127.0.0.1:8000
```

## Assets

### tools/banner.txt

ASCII banner used by local tooling (e.g., container build scripts).
