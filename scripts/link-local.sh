#!/usr/bin/env bash
set -euo pipefail
shopt -s nullglob

# link-local.sh — Create LiveSpec command/agent symlinks in a project's .claude/ directory
#
# Usage: link-local.sh <project-dir> <livespec-dir>
#
# Creates symlinks:
#   .claude/commands/spec.<name>.md → <livespec-dir>/commands/<name>.md
#   .claude/agents/<name>.md        → <livespec-dir>/agents/<name>.md
#
# Excludes: init.md and migrate.md (these stay global only)

PROJECT_DIR="${1:?Usage: link-local.sh <project-dir> <livespec-dir>}"
LIVESPEC_DIR="${2:?Usage: link-local.sh <project-dir> <livespec-dir>}"

# Resolve to absolute paths
PROJECT_DIR="$(cd "$PROJECT_DIR" && pwd)"
LIVESPEC_DIR="$(cd "$LIVESPEC_DIR" && pwd)"

# Verify directories exist
if [[ ! -d "$LIVESPEC_DIR/commands" ]]; then
  echo "ERROR: $LIVESPEC_DIR/commands does not exist" >&2
  exit 1
fi
if [[ ! -d "$LIVESPEC_DIR/agents" ]]; then
  echo "ERROR: $LIVESPEC_DIR/agents does not exist" >&2
  exit 1
fi

# Create target directories
mkdir -p "$PROJECT_DIR/.claude/commands"
mkdir -p "$PROJECT_DIR/.claude/agents"

# Counters
cmd_count=0
agent_count=0
errors=0

# Link commands (exclude init.md and migrate.md)
for src in "$LIVESPEC_DIR"/commands/*.md; do
  name="$(basename "$src" .md)"
  # Skip init and migrate — they stay global
  if [[ "$name" == "init" || "$name" == "migrate" ]]; then
    continue
  fi
  dest="$PROJECT_DIR/.claude/commands/spec.${name}.md"
  ln -sf "$src" "$dest"
  cmd_count=$((cmd_count + 1))
done

# Link agents
for src in "$LIVESPEC_DIR"/agents/*.md; do
  name="$(basename "$src")"
  dest="$PROJECT_DIR/.claude/agents/${name}"
  ln -sf "$src" "$dest"
  agent_count=$((agent_count + 1))
done

# Validate all symlinks resolve and are readable
for link in "$PROJECT_DIR"/.claude/commands/spec.*.md; do
  if ! [[ -e "$link" && -r "$link" ]]; then
    echo "ERROR: broken or unreadable symlink: $link → $(readlink "$link")" >&2
    errors=$((errors + 1))
  fi
done
for link in "$PROJECT_DIR"/.claude/agents/*.md; do
  if ! [[ -e "$link" && -r "$link" ]]; then
    echo "ERROR: broken or unreadable symlink: $link → $(readlink "$link")" >&2
    errors=$((errors + 1))
  fi
done

if [[ $errors -gt 0 ]]; then
  echo "FAILED: $errors broken symlink(s)" >&2
  exit 1
fi

echo "Linked $cmd_count commands and $agent_count agents"
exit 0
