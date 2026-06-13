#!/usr/bin/env bash
# Migration v22 wrapper: scaffold linter config only when conventions gates are
# present and can provide the managed limits.

set -euo pipefail

PROJECT_DIR="${1:?Usage: migrate-conventions-scaffold.sh <project-dir> <livespec-dir>}"
_LIVESPEC_DIR="${2:?Usage: migrate-conventions-scaffold.sh <project-dir> <livespec-dir>}"

cd "$PROJECT_DIR"

if [[ ! -f .specs/conventions-gates.yaml ]]; then
  echo "conventions gates missing; no-op"
  exit 0
fi

livespec conventions scaffold --apply
