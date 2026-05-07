#!/usr/bin/env bash
# migrate-surfaces.sh — Migration v11 wrapper.
#
# Invokes `generate-surfaces.js --migrate-surfaces` from PROJECT_DIR so that
# downstream projects with split `tests/e2e/` + `tests/visual/` layouts get
# their visual surface(s) appended to `.specs/surfaces.yaml` automatically
# during `/spec.migrate`.
#
# The text-level append in `runMigrateSurfaces()` is idempotent and
# byte-for-byte preserves existing manifest entries — re-running on a
# already-migrated manifest is a no-op.
#
# If `.specs/surfaces.yaml` is absent, the script bootstraps a fresh
# manifest via the standard `main()` path (no flag).
#
# Usage (called by scripts/migrate.sh): migrate-surfaces.sh <project> <livespec>

set -euo pipefail

PROJECT_DIR="${1:?Usage: migrate-surfaces.sh <project-dir> <livespec-dir>}"
LIVESPEC_DIR="${2:?Usage: migrate-surfaces.sh <project-dir> <livespec-dir>}"

cd "$PROJECT_DIR"

if [[ -f .specs/surfaces.yaml ]]; then
  node "$LIVESPEC_DIR/scripts/generate-surfaces.js" --migrate-surfaces
else
  # No manifest yet — generate one from scratch (multi-surface aware).
  node "$LIVESPEC_DIR/scripts/generate-surfaces.js"
fi
