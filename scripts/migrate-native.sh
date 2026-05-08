#!/usr/bin/env bash
# migrate-native.sh — Migration v12 wrapper.
#
# Invokes `generate-surfaces.js --migrate-native` from PROJECT_DIR so that
# downstream projects with native (Xcode / Android Gradle) layouts get
# their iOS, watchOS, and Android surfaces appended to
# `.specs/surfaces.yaml` automatically during `/spec.migrate`.
#
# The text-level append in `runMigrateNative()` is idempotent and
# byte-for-byte preserves existing manifest entries — re-running on an
# already-migrated manifest is a no-op.
#
# If `.specs/surfaces.yaml` is absent, the script bootstraps a fresh
# manifest via the standard `main()` path (no flag), which is now
# multi-platform aware (Playwright + xcuitest + maestro).
#
# Usage (called by scripts/migrate.sh): migrate-native.sh <project> <livespec>

set -euo pipefail

PROJECT_DIR="${1:?Usage: migrate-native.sh <project-dir> <livespec-dir>}"
LIVESPEC_DIR="${2:?Usage: migrate-native.sh <project-dir> <livespec-dir>}"

# `generate-surfaces.js` discovers files relative to the project cwd and writes
# `.specs/surfaces.yaml` in place, so the wrapper must run from the target repo.
cd "$PROJECT_DIR"

# Preserve legacy manifests with the append-only migration path when they already
# exist; fall back to full generation only for projects that have no manifest yet.
if [[ -f .specs/surfaces.yaml ]]; then
  # This Node entrypoint exits non-zero on detection or write failures and
  # updates the existing manifest in place without rewriting unrelated content.
  node "$LIVESPEC_DIR/scripts/generate-surfaces.js" --migrate-native
else
  # No manifest yet — generate one from scratch (multi-platform aware).
  # This writes a fresh `.specs/surfaces.yaml` based on the current project scan.
  node "$LIVESPEC_DIR/scripts/generate-surfaces.js"
fi
