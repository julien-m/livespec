#!/usr/bin/env bash
# LiveSpec traceability anchors
# @spec(FR-012)

set -euo pipefail

# Migration v14 wrapper: refresh command links after command-audit hardening.

PROJECT_DIR="${1:?Usage: migrate-command-validation.sh <project-dir> <livespec-dir>}"
LIVESPEC_DIR="${2:?Usage: migrate-command-validation.sh <project-dir> <livespec-dir>}"

if [[ -d "$PROJECT_DIR/.claude/commands" ]]; then
  echo "  ▸ migrate-command-validation: refreshing command symlinks"
  bash "$LIVESPEC_DIR/scripts/link-local.sh" "$PROJECT_DIR" "$LIVESPEC_DIR"
else
  echo "  ▸ migrate-command-validation: .claude/commands missing, skipping link refresh"
fi

echo "  ✓ migrate-command-validation complete"
