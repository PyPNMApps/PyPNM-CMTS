# FILE: tools/smoke/run-all.sh
#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

set -euo pipefail
IFS=$'\n\t'

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

"${REPO_ROOT}/tools/smoke/ops-smoke.sh"
