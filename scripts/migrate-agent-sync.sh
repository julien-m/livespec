#!/usr/bin/env bash
# LiveSpec traceability anchors
# @spec(FR-006)

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
      ../../commands/*|../../agents/*)
        rm -f "$link"
        ;;
    esac
  done
}

cleanup_project_canonical_symlinks() {
  local link
  for link in "$PROJECT_DIR"/.agent-sync/skills/spec-* "$PROJECT_DIR"/.agent-sync/agents/livespec-*; do
    [[ -L "$link" ]] || continue
    local target
    target="$(readlink "$link")"
    case "$target" in
      "$LIVESPEC_DIR"/.agent-sync/skills/spec-*|"$LIVESPEC_DIR"/.agent-sync/agents/livespec-*)
        rm -f "$link"
        ;;
    esac
  done

  for link in "$PROJECT_DIR"/.agent-sync/rules/commands.md "$PROJECT_DIR"/.agent-sync/rules/routing.md; do
    [[ -L "$link" ]] || continue
    local target
    target="$(readlink "$link")"
    case "$target" in
      "$LIVESPEC_DIR"/.agent-sync/rules/livespec/commands.md|"$LIVESPEC_DIR"/.agent-sync/rules/livespec/routing.md)
        rm -f "$link"
        ;;
    esac
  done
}

cleanup_project_provider_symlinks() {
  local link
  for link in \
    "$PROJECT_DIR"/.claude/skills/spec-* \
    "$PROJECT_DIR"/.agents/skills/spec-* \
    "$PROJECT_DIR"/.claude/agents/livespec-*.md \
    "$PROJECT_DIR"/.codex/agents/livespec-*.toml \
    "$PROJECT_DIR"/.claude/rules/commands.md \
    "$PROJECT_DIR"/.claude/rules/routing.md; do
    [[ -L "$link" ]] || continue
    local target
    target="$(readlink "$link")"
    case "$target" in
      "$PROJECT_DIR"/.agent-sync/skills/spec-*|"$PROJECT_DIR"/.agent-sync/agents/livespec-*|"$PROJECT_DIR"/.agent-sync/rules/commands.md|"$PROJECT_DIR"/.agent-sync/rules/routing.md|.agent-sync/skills/spec-*|.agent-sync/agents/livespec-*|.agent-sync/rules/commands.md|.agent-sync/rules/routing.md)
        rm -f "$link"
        ;;
    esac
  done
}

cleanup_legacy_symlinks
cleanup_project_canonical_symlinks
cleanup_project_provider_symlinks
bash "$LIVESPEC_DIR/scripts/sync-agent-assets.sh" "$PROJECT_DIR" "$LIVESPEC_DIR" \
  --scope project --targets all
