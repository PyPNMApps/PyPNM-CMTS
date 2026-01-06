<p align="center">
  <a href="docs/index.md">
    <picture>
      <source srcset="docs/images/pypnm-cmts-hp-dark-43.png"
              media="(prefers-color-scheme: dark)" />
      <img src="docs/images/pypnm-cmts-hp-light-43.png"
           alt="PyPNM-CMTS Logo"
           width="220"
           style="border-radius: 24px;" />
    </picture>
  </a>
</p>

# PyPNM-CMTS - CMTS Operations Toolkit for PyPNM (Under Development)

[![PyPI version](https://badge.fury.io/py/pypnm-docsis-cmts.svg)](https://badge.fury.io/py/pypnm-docsis-cmts)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](./LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)

PyPNM-CMTS extends the PyPNM toolkit with CMTS-focused automation, validation, and
operational workflows. It installs `pypnm-docsis` as the base library and adds CMTS
capabilities on top.

## Table of contents

- [Choose your path](#choose-your-path)
- [Getting started](#getting-started)
  - [Install from PyPI (library only)](#install-from-pypi-library-only)
  - [1) Clone](#1-clone)
  - [2) Install](#2-install)
  - [3) Activate the virtual environment](#3-activate-the-virtual-environment)
  - [4) Run the CLI](#4-run-the-cli)
- [Documentation](#documentation)
- [License](#license)
- [Maintainer](#maintainer)

## Choose your path

| Path | Description |
| --- | --- |
| [Use PyPNM-CMTS as a library](#install-from-pypi-library-only) | Install `pypnm-docsis-cmts` into an existing Python environment. |
| [Run the full repo](#1-clone) | Clone the repo and use the CLI + tools stack. |

## Getting started

### Install from PyPI (library only)

If you only need the library, install from PyPI:

  ```bash
  pip install pypnm-docsis-cmts
  ```

### 1) Clone

  ```bash
  git clone https://github.com/PyPNMApps/PyPNM-CMTS.git
  cd PyPNM-CMTS
```

### 2) Install

Run the installer:

  ```bash
  ./install.sh
  ```

Optional: use a custom venv directory:

  ```bash
  ./install.sh .env-dev
  ```

Optional: development install with extra tooling:

  ```bash
  ./install.sh --development
  ```

Optional: update from the latest GA or hot-fix tag:

  ```bash
  ./install.sh --update-ga
  ./install.sh --update-hot-fix
  ```

Cleanup and uninstall:

  ```bash
  ./install.sh --clean
  ./install.sh --uninstall
  ```

### 3) Activate the virtual environment

If you used the installer defaults, activate the `.env` environment:

  ```bash
  source .env/bin/activate
  ```

### 4) Run the CLI

  ```bash
  pypnm-cmts --version
  ```

### 5) Run the FastAPI service

  ```bash
  pypnm-cmts serve
  ```

The service binds to `127.0.0.1:8000` by default and reads CMTS adapter
settings from `system.json`. Use `pypnm-cmts config-menu` to set the CMTS
hostname and SNMP communities, or pass `--cmts-hostname`/`--read-community`
overrides at runtime.

## Documentation

- Docs are being assembled; see `docs/` as the starting point.
- [CLI examples](docs/examples/cli.md)

## SNMP notes

- SNMPv2c is supported  
- SNMPv3 is currently stubbed and not yet supported

## CableLabs specifications & MIBs

- [CM-SP-MULPIv3.1](https://www.cablelabs.com/specifications/CM-SP-MULPIv3.1)  
- [CM-SP-CCAP-OSSIv3.1](https://www.cablelabs.com/specifications/CM-SP-CCAP-OSSIv3.1)  
- [CM-SP-MULPIv4.0](https://www.cablelabs.com/specifications/CM-SP-MULPIv4.0)  
- [CM-SP-CCAP-OSSIv4.0](https://www.cablelabs.com/specifications/CM-SP-CCAP-OSSIv4.0)  
- [DOCSIS MIBs](https://mibs.cablelabs.com/MIBs/DOCSIS/)

## License

[`Apache License 2.0`](./LICENSE) and [`NOTICE`](./NOTICE)

## Maintainer

Maurice Garcia

- [Email](mailto:mgarcia01752@outlook.com)
- [LinkedIn](https://www.linkedin.com/in/mauricemgarcia/)
