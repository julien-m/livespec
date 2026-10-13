#!/usr/bin/env bash
# Migration v23 wrapper: repair bootstrap artifacts generated before feature 080 FR-005.
# @spec FR-006: Migration v23 bootstrap repair — .specs/features/080-autonomous-from-code-recovery/spec.md#fr-006
set -euo pipefail
PROJECT_DIR="${1:?Usage: migrate-init-bootstrap-repair.sh <project-dir> <livespec-dir>}"
LIVESPEC_DIR="${2:?Usage: migrate-init-bootstrap-repair.sh <project-dir> <livespec-dir>}"
export PYTHONPATH="$LIVESPEC_DIR${PYTHONPATH:+:$PYTHONPATH}"
PYTHON_BIN="python3"
[[ ! -x "$LIVESPEC_DIR/.venv/bin/python" ]] || PYTHON_BIN="$LIVESPEC_DIR/.venv/bin/python"
exec "$PYTHON_BIN" -B -m validator.init_bootstrap_repair "$PROJECT_DIR"
