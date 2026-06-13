#!/usr/bin/env bash
# Migration v22 wrapper: initialize conventions gates when a project has the
# source files needed for deterministic gate generation.

set -euo pipefail

PROJECT_DIR="${1:?Usage: migrate-conventions-gates-init.sh <project-dir> <livespec-dir>}"
_LIVESPEC_DIR="${2:?Usage: migrate-conventions-gates-init.sh <project-dir> <livespec-dir>}"

cd "$PROJECT_DIR"

if [[ -f .specs/conventions-gates.yaml ]]; then
  echo "conventions gates already present; no-op"
  exit 0
fi

if [[ ! -f .specs/constitution.md || ! -f .specs/stacks/_default.md ]]; then
  echo "conventions gates prerequisites missing; no-op"
  exit 0
fi

livespec conventions gates init --force || true
