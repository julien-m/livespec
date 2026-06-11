#!/usr/bin/env bash
# LiveSpec traceability anchors
# @spec(FR-010)

set -euo pipefail

# Migration v21 wrapper: scaffold the journey fixtures bootstrap contract with
# the LiveSpec version being applied, not a possibly stale globally installed
# CLI. Exit 0 covers scaffolded, already-present, and no-fixture-journeys
# outcomes (AC-012) — only a write failure exits non-zero.

PROJECT_DIR="${1:?Usage: migrate-journeys-fixtures-scaffold.sh <project-dir> <livespec-dir>}"
LIVESPEC_DIR="${2:?Usage: migrate-journeys-fixtures-scaffold.sh <project-dir> <livespec-dir>}"

cd "$PROJECT_DIR"
PYTHONPATH="$LIVESPEC_DIR${PYTHONPATH:+:$PYTHONPATH}" python3 -m validator.cli journey fixtures scaffold
