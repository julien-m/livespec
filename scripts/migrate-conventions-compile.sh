#!/usr/bin/env bash
# Migration v22 wrapper: compile the conventions rulebook only for projects that
# already have a refreshed `.conventions/manifest.yaml`.

set -euo pipefail

PROJECT_DIR="${1:?Usage: migrate-conventions-compile.sh <project-dir> <livespec-dir>}"
_LIVESPEC_DIR="${2:?Usage: migrate-conventions-compile.sh <project-dir> <livespec-dir>}"

cd "$PROJECT_DIR"

if [[ ! -f .conventions/manifest.yaml ]]; then
  echo "conventions manifest missing; no-op"
  exit 0
fi

livespec conventions compile --force
