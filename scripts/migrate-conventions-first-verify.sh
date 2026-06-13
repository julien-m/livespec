#!/usr/bin/env bash
# Migration v22 wrapper: record the first conventions debt report without
# blocking migration. Pipeline runs enforce blocking receipts later.

set -euo pipefail

PROJECT_DIR="${1:?Usage: migrate-conventions-first-verify.sh <project-dir> <livespec-dir>}"
_LIVESPEC_DIR="${2:?Usage: migrate-conventions-first-verify.sh <project-dir> <livespec-dir>}"

cd "$PROJECT_DIR"

if [[ ! -f .specs/conventions-gates.yaml ]]; then
  echo "conventions gates missing; first verify no-op"
  exit 0
fi

livespec conventions verify --report || true
exit 0
