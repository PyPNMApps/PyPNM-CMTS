# PyPNM-CMTS Release Guide

## Table of contents

[1. Branch model](#1-branch-model)

[2. Version source of truth](#2-version-source-of-truth)

[3. Versioning scheme](#3-versioning-scheme)

[4. Release script overview](#4-release-script-overview)

[5. Release modes and examples](#5-release-modes-and-examples)

[6. Preflight controls](#6-preflight-controls)

[7. Quick reference](#7-quick-reference)

[8. Release workflow](#8-release-workflow)

This guide follows the PyPNM release strategy and uses the same four-part versioning scheme.
The release entry point is `tools/release/release.py`.

## 1. Branch model

PyPNM-CMTS currently follows a single-branch release model:

* `main` is the release branch.
* Feature branches are optional and short-lived.

## 2. Version source of truth

The canonical version lives in:

```text
src/pypnm_cmts/version.py
```

The `pyproject.toml` version mirrors it and must match at all times.

Example:

```python
from __future__ import annotations

__all__ = ["__version__"]

# MAJOR.MINOR.MAINTENANCE.BUILD
__version__: str = "0.1.0.0"
```

## 3. Versioning scheme

PyPNM-CMTS uses a four-part version:

```text
MAJOR.MINOR.MAINTENANCE.BUILD
```

Guidelines:

* `MAJOR` for breaking changes.
* `MINOR` for backward-compatible features.
* `MAINTENANCE` for compatible bug fixes.
* `BUILD` for small hotfixes or rebuilds.

All four segments must be numeric.

## 4. Release script overview

The release script:

* Reads `src/pypnm_cmts/version.py`.
* Confirms it matches `pyproject.toml`.
* Computes or accepts a target version.
* Runs tests (unless skipped).
* Builds docs.
* Commits, tags, and optionally pushes.

Docker and Kubernetes preflight steps are currently skipped by default in PyPNM-CMTS.
The release script prints a reminder so this can be revisited later.

## 5. Release modes and examples

### 5.1 Automatic maintenance release (default)

```bash
REPO_ROOT="/path/to/PyPNM-CMTS"
python "$REPO_ROOT/tools/release/release.py"
```

### 5.2 Automatic next version by mode (`--next`)

```bash
REPO_ROOT="/path/to/PyPNM-CMTS"
python "$REPO_ROOT/tools/release/release.py" --next minor
python "$REPO_ROOT/tools/release/release.py" --next maintenance
python "$REPO_ROOT/tools/release/release.py" --next build
```

### 5.3 Explicit version (`--version`)

```bash
REPO_ROOT="/path/to/PyPNM-CMTS"
python "$REPO_ROOT/tools/release/release.py" --version 0.2.0.0
```

### 5.4 Dry run (`--dry-run`)

```bash
REPO_ROOT="/path/to/PyPNM-CMTS"
python "$REPO_ROOT/tools/release/release.py" --dry-run
```

## 6. Preflight controls

```bash
REPO_ROOT="/path/to/PyPNM-CMTS"
python "$REPO_ROOT/tools/release/release.py" --skip-tests
```

## 7. Quick reference

* Default release (auto maintenance bump):

  ```bash
  REPO_ROOT="/path/to/PyPNM-CMTS"
  python "$REPO_ROOT/tools/release/release.py"
  ```

* Explicit version:

  ```bash
  REPO_ROOT="/path/to/PyPNM-CMTS"
  python "$REPO_ROOT/tools/release/release.py" --version 0.2.0.0
  ```

* Dry run:

  ```bash
  REPO_ROOT="/path/to/PyPNM-CMTS"
  python "$REPO_ROOT/tools/release/release.py" --dry-run
  ```

## 8. Release workflow

Use this flow for routine releases on `main`:

```bash
REPO_ROOT="/path/to/PyPNM-CMTS"
cd "$REPO_ROOT"
git checkout main
git pull origin main
python tools/release/release.py --dry-run
python tools/release/release.py
```

Hot-fix releases use the `hot-fix` branch and bump the `BUILD` segment:

```bash
REPO_ROOT="/path/to/PyPNM-CMTS"
cd "$REPO_ROOT"
git fetch origin
git checkout hot-fix
git pull origin hot-fix
python tools/release/release.py --next build --branch hot-fix
```

If you installed aliases with `scripts/install_aliases.sh`, you can use:

```bash
pypnm-cmts-release
pypnm-cmts-release-hot-fix
```
