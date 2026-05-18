#!/usr/bin/env bash
set -euo pipefail

# Migration v16 wrapper: remove only legacy LiveSpec-managed provider symlinks
# and sync portable `.agent-sync` assets through cc-hub.

PROJECT_DIR="${1:?Usage: migrate-agent-sync.sh <project-dir> <livespec-dir>}"
LIVESPEC_DIR="${2:?Usage: migrate-agent-sync.sh <project-dir> <livespec-dir>}"

cleanup_legacy_symlinks() {
  local link
  for link in "$PROJECT_DIR"/.claude/commands/spec*.md "$PROJECT_DIR"/.claude/agents/livespec-*.md; do
    [[ -L "$link" ]] || continue
    local target
    target="$(readlink "$link")"
    case "$target" in
      "$LIVESPEC_DIR"/commands/*|"$LIVESPEC_DIR"/agents/*)
        rm -f "$link"
        ;;
    esac
  done
}

cleanup_legacy_symlinks
bash "$LIVESPEC_DIR/scripts/sync-agent-assets.sh" "$PROJECT_DIR" "$LIVESPEC_DIR" \
  --scope project --targets all
