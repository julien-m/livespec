#!/usr/bin/env bash
# Thin compatibility entry point for the observed autonomous initialization backend.
# @spec FR-003: Preserve selected target and flags — .specs/features/080-autonomous-from-code-recovery/spec.md#fr-003
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LIVESPEC_ROOT="$(dirname "$SCRIPT_DIR")"
# -B prevents readonly verification from creating project or package bytecode caches.
export PYTHONPATH="$LIVESPEC_ROOT${PYTHONPATH:+:$PYTHONPATH}"
PYTHON_BIN="python3"
[[ ! -x "$LIVESPEC_ROOT/.venv/bin/python" ]] || PYTHON_BIN="$LIVESPEC_ROOT/.venv/bin/python"
exec "$PYTHON_BIN" -B -m validator.init_from_code "$@"
