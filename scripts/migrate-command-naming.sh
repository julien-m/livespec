#!/usr/bin/env bash
# LiveSpec traceability anchors
# @spec(FR-008)

set -euo pipefail

# Migration v15 wrapper: install hyphenated slash-command links and keep dotted aliases.

PROJECT_DIR="${1:?Usage: migrate-command-naming.sh <project-dir> <livespec-dir>}"
LIVESPEC_DIR="${2:?Usage: migrate-command-naming.sh <project-dir> <livespec-dir>}"

if [[ -d "$PROJECT_DIR/.claude/commands" ]]; then
  echo "  ▸ migrate-command-naming: creating /spec-* links and preserving /spec.* aliases"
  bash "$LIVESPEC_DIR/scripts/link-local.sh" "$PROJECT_DIR" "$LIVESPEC_DIR"
else
  echo "  ▸ migrate-command-naming: .claude/commands missing, skipping link refresh"
fi

echo "  ✓ migrate-command-naming complete"
