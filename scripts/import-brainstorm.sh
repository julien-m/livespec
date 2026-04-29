#!/usr/bin/env bash
# import-brainstorm.sh — Auto-import brainstorm artifacts into existing .specs/
#
# Usage: import-brainstorm.sh <project-dir> <livespec-dir>
#
# Behavior:
#   - Silent no-op if no brainstorm artifacts found
#   - Validates grammar; aborts on violations
#   - Plans + applies in refine mode without confirmation
#
# Migration v9.

set -euo pipefail

PROJECT_DIR="${1:?Usage: import-brainstorm.sh <project-dir> <livespec-dir>}"
LIVESPEC_DIR="${2:?Usage: import-brainstorm.sh <project-dir> <livespec-dir>}"

PROJECT_DIR="$(cd "$PROJECT_DIR" && pwd)"
LIVESPEC_DIR="$(cd "$LIVESPEC_DIR" && pwd)"

# Detection — silent no-op if nothing to import
shopt -s nullglob
flow_files=("$PROJECT_DIR"/specs/flows/*.md)
shopt -u nullglob
manifest="$PROJECT_DIR/mockups/manifest.json"
profile="$PROJECT_DIR/project-profile.md"

if [[ ${#flow_files[@]} -eq 0 && ! -f "$manifest" && ! -f "$profile" ]]; then
  echo "  · no brainstorm artifacts detected — skipping import"
  exit 0
fi

echo "  · brainstorm artifacts detected — running refine-mode import"

# Resolve Python interpreter — prefer LiveSpec repo's venv when available
if [[ -x "$LIVESPEC_DIR/.venv/bin/python" ]]; then
  PYBIN="$LIVESPEC_DIR/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PYBIN="python3"
else
  echo "  ✗ no python3 interpreter found" >&2
  exit 1
fi

run_brainstorm() {
  PYTHONPATH="$LIVESPEC_DIR" "$PYBIN" -m validator.brainstorm "$@"
}

# Step 1 — Validate grammar; abort on violations
if ! run_brainstorm validate --cwd "$PROJECT_DIR" --format compact; then
  echo "  ✗ brainstorm validation failed — migration aborted, .specs/ untouched" >&2
  exit 1
fi

# Step 2 — Build refine-mode plan
plan_path="$PROJECT_DIR/.livespec-import-plan.json"
run_brainstorm plan --cwd "$PROJECT_DIR" --mode refine --out "$plan_path"

# Step 3 — Apply (no confirmation)
run_brainstorm apply "$plan_path"

# Step 4 — Cleanup intermediate plan file
rm -f "$plan_path"

echo "  ✓ brainstorm import complete"
