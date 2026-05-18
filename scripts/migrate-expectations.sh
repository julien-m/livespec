#!/usr/bin/env bash
# migrate-expectations.sh — Migration v13 wrapper.
#
# Backfills feature 039 (command expectations + /spec-verify-output) and
# feature 040 (rich expectations + --preview/--save) wiring on projects
# initialised before v13:
#
#   1. Re-link commands/agents through the patched `link-local.sh` so that
#      new commands (notably `spec-verify-output`) appear and orphan
#      `spec.*.expectations.md` symlinks created by the buggy pre-fix
#      `link-local.sh` are removed.
#   2. Install the `last_reviewed` pre-commit hook
#      (`hooks/livespec-last-reviewed.py`) and append the matching
#      `.specs/.runs/` / `.specs/.previews/` gitignore entries.
#
# Both inner scripts are idempotent: re-running this wrapper on an
# already-migrated project is a no-op.
#
# Usage (called by scripts/migrate.sh): migrate-expectations.sh <project> <livespec>

set -euo pipefail

PROJECT_DIR="${1:?Usage: migrate-expectations.sh <project-dir> <livespec-dir>}"
LIVESPEC_DIR="${2:?Usage: migrate-expectations.sh <project-dir> <livespec-dir>}"

PROJECT_DIR="$(cd "$PROJECT_DIR" && pwd)"
LIVESPEC_DIR="$(cd "$LIVESPEC_DIR" && pwd)"

# `link-local.sh` is only meaningful for projects that already opted into the
# `.claude/commands/` layout. Skip silently when the directory does not exist
# (e.g. projects that drive LiveSpec exclusively via the global commands).
if [[ -d "${PROJECT_DIR}/.claude/commands" ]]; then
  echo "  ▸ migrate-expectations: refreshing .claude/commands symlinks"
  bash "${LIVESPEC_DIR}/scripts/link-local.sh" "${PROJECT_DIR}" "${LIVESPEC_DIR}"
else
  echo "  (no .claude/commands/ in ${PROJECT_DIR} — skipping link refresh)"
fi

echo "  ▸ migrate-expectations: installing last_reviewed pre-commit hook"
bash "${LIVESPEC_DIR}/scripts/install-hooks.sh" "${PROJECT_DIR}" "${LIVESPEC_DIR}"

echo "  ✓ migrate-expectations complete"
