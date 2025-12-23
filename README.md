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

[![PyPI version](https://badge.fury.io/py/pypnm-cmts.svg)](https://badge.fury.io/py/pypnm-cmts)
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
| [Use PyPNM-CMTS as a library](#install-from-pypi-library-only) | Install `pypnm-cmts` into an existing Python environment. |
| [Run the full repo](#1-clone) | Clone the repo and use the CLI + tools stack. |

## Getting started

### Install from PyPI (library only)

If you only need the library, install from PyPI:

  ```bash
  pip install pypnm-cmts
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

### 3) Activate the virtual environment

If you used the installer defaults, activate the `.env` environment:

  ```bash
  source .env/bin/activate
  ```

### 4) Run the CLI

  ```bash
  pypnm-cmts --version
  ```

## Documentation

- Docs are being assembled; see `docs/` as the starting point.
- [CLI examples](docs/examples/cli.md)

## License

[`Apache License 2.0`](./LICENSE) and [`NOTICE`](./NOTICE)

## Maintainer

Maurice Garcia

- [Email](mailto:mgarcia01752@outlook.com)
- [LinkedIn](https://www.linkedin.com/in/mauricemgarcia/)
