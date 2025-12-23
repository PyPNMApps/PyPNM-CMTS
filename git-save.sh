#!/usr/bin/env bash
set -euo pipefail

COMMIT_MESSAGE="${1:-Next}"

git add -A
git commit -m "${COMMIT_MESSAGE}"
git push
