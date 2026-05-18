#!/usr/bin/env bash
set -euo pipefail
shopt -s nullglob

# link-local.sh — Create LiveSpec command/agent symlinks in a project's .claude/ directory
#
# Usage: link-local.sh <project-dir> <livespec-dir>
#
# Creates symlinks:
#   .claude/commands/spec-<name>.md → <livespec-dir>/commands/spec-<name>.md
#   .claude/commands/spec.<name>.md → <livespec-dir>/commands/spec-<name>.md (legacy alias)
#   .claude/agents/<name>.md        → <livespec-dir>/agents/<name>.md
#
# Excludes: spec-init.md and spec-migrate.md (these stay global only)

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

# Clean up orphan symlinks from older link-local versions that did not
# filter sidecar metadata files (e.g. `*.expectations.md`). These end up
# as `.claude/commands/spec.<cmd>.expectations.md` and pollute the slash
# command menu. Remove them before re-linking so the operation is
# self-healing on re-runs / migrations.
for orphan in "$PROJECT_DIR"/.claude/commands/spec.*.expectations.md; do
  [[ -L "$orphan" ]] || continue
  rm -f "$orphan"
done

# Link commands (exclude spec-init.md and spec-migrate.md + sidecar metadata files)
for src in "$LIVESPEC_DIR"/commands/*.md; do
  name="$(basename "$src" .md)"
  # Skip sidecar files (e.g. *.expectations.md) — they are metadata,
  # consumed by `livespec verify-output` directly from the LiveSpec
  # checkout, never invoked as slash commands.
  if [[ "$name" == *.expectations ]]; then
    continue
  fi
  # Only canonical command source files are linked.
  if [[ "$name" != spec-* ]]; then
    continue
  fi
  short_name="${name#spec-}"
  # Skip init and migrate — they stay global
  if [[ "$short_name" == "init" || "$short_name" == "migrate" ]]; then
    continue
  fi
  dest="$PROJECT_DIR/.claude/commands/${name}.md"
  ln -sf "$src" "$dest"
  legacy_dest="$PROJECT_DIR/.claude/commands/spec.${short_name}.md"
  ln -sf "$src" "$legacy_dest"
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
for link in "$PROJECT_DIR"/.claude/commands/spec*.md; do
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
