# Install

Installation and setup notes for PyPNM-CMTS.

## Quick install

Run the installer from the repo root:

```bash
./install.sh
```

Before running the installer, make sure `PYTHONPATH` is not pointing at another
PyPNM source checkout. A leaked value such as `/home/user/Projects/PyPNM/src`
can cause PyPNM-CMTS to import the wrong lower-layer runtime, which redirects
logs, `.data`, and operation state outside this repo.

Check and clear it from a clean shell if needed:

```bash
echo "$PYTHONPATH"
unset PYTHONPATH
```

## Post-install quickstart

Activate the virtual environment:

```bash
source .env/bin/activate
```

Run the CLI help:

```bash
pypnm-cmts --help
```

Run the service help:

```bash
pypnm-cmts serve --help
```

Configure system.json with the interactive config menu:

```bash
pypnm-cmts config-menu
```

Start the FastAPI service:

```bash
pypnm-cmts serve
```

The service binds to `127.0.0.1:8080` by default and loads CMTS adapter
settings from `system.json`. Use `pypnm-cmts config-menu` to set the CMTS
hostname and SNMP communities, or pass `--cmts-hostname` and `--read-community`
as overrides.

Run tests:

```bash
python -m pytest -v
```

Run docs locally:

```bash
python -m mkdocs serve -a 127.0.0.1:8081
```

```mermaid
flowchart TD
  A[Install] --> B[Activate Venv]
  B --> C[Run config-menu]
  C --> D[Serve API]
  D --> E[Run Tests]
  E --> F[Serve Docs]
```

## Common modes

Use a custom virtual environment directory:

```bash
./install.sh .env-dev
```

Development mode:

```bash
./install.sh --development
```

Development mode attempts to install gitleaks via the system package manager and
falls back to a GitHub release download when the package is unavailable.

The installer now stops early if `PYTHONPATH` points at an external source tree.
This is intentional and protects the runtime from silently importing the wrong
`pypnm` package.

Update to the latest GA or hot-fix tag (or pass a tag explicitly):

```bash
./install.sh --update-ga
./install.sh --update-ga v0.1.39.0
./install.sh --update-hot-fix
./install.sh --update-hot-fix v0.1.39.1
```

Update `pypnm-docsis` in the active virtual environment:

```bash
./install.sh --update-development-pypnm-docsis
./install.sh --update-development-pypnm-docsis v1.4.2.0
```

Without a tag, the installer upgrades to the latest prerelease. With a tag or
version, it installs that exact `pypnm-docsis` release.

Clean or uninstall local install artifacts:

```bash
./install.sh --clean
./install.sh --uninstall
```
