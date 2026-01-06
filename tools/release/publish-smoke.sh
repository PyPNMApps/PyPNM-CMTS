#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

set -euo pipefail

if [[ "${1-}" == "--help" ]]; then
  echo "Usage: tools/release/publish-smoke.sh [--upload]"
  exit 0
fi

upload=false
if [[ "${1-}" == "--upload" ]]; then
  upload=true
fi

python -m build
python -m twine check dist/*

if [[ "$upload" == "true" ]]; then
  pypnm-cmts-publish --yes
fi
