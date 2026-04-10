#!/usr/bin/env bash
set -euo pipefail

# scaffold-visual-testing.sh — Retrofit visual testing infrastructure into a project
#
# Usage: scaffold-visual-testing.sh <project-dir> <livespec-dir>
#
# Called by migrate.sh for migration v3.
# Idempotent: skips scaffold if visual.ts already exists and is valid.
#             Overwrites if required symbols (compareRegression, compareDesign) are missing.
# Self-validates exit criteria before exit 0.
#
# Exit codes:
#   0 — success (visual.ts in place, deps installed or no package.json)
#   1 — deps required but not installed (yarn/pnpm detected, no lock file, or install failed)

PROJECT_DIR="${1:?Usage: scaffold-visual-testing.sh <project-dir> <livespec-dir>}"
LIVESPEC_DIR="${2:?Usage: scaffold-visual-testing.sh <project-dir> <livespec-dir>}"

PROJECT_DIR="$(cd "$PROJECT_DIR" && pwd)"
LIVESPEC_DIR="$(cd "$LIVESPEC_DIR" && pwd)"

TEMPLATE_SRC="$LIVESPEC_DIR/templates/visual.ts"
HELPER_DEST="$PROJECT_DIR/tests/e2e/helpers/visual.ts"
PKG_JSON="$PROJECT_DIR/package.json"
DEPS="pixelmatch pngjs sharp @types/pixelmatch @types/pngjs"

has_required_deps() {
  (
    cd "$PROJECT_DIR" &&
      node -e "const p=require('./package.json'); process.exit((p.devDependencies?.pixelmatch && p.devDependencies?.sharp) ? 0 : 1)" 2>/dev/null
  )
}

# --- Verify template exists ---

if [[ ! -f "$TEMPLATE_SRC" ]]; then
  echo "ERROR: Template not found: $TEMPLATE_SRC" >&2
  exit 1
fi

# --- Scaffold visual.ts ---

if [[ -f "$HELPER_DEST" ]]; then
  echo "  · tests/e2e/helpers/visual.ts already exists — validating"
  # Overwrite if any required symbol is missing (stale or incomplete file)
  NEEDS_OVERWRITE=false
  for symbol in compareRegression compareDesign; do
    if ! grep -q "$symbol" "$HELPER_DEST"; then
      echo "  ! Missing '$symbol' in existing visual.ts — overwriting with template"
      NEEDS_OVERWRITE=true
      break
    fi
  done
  if [[ "$NEEDS_OVERWRITE" == true ]]; then
    cp "$TEMPLATE_SRC" "$HELPER_DEST"
    echo "  ✓ tests/e2e/helpers/visual.ts updated from template"
  else
    echo "  ✓ tests/e2e/helpers/visual.ts already valid"
  fi
else
  mkdir -p "$(dirname "$HELPER_DEST")"
  cp "$TEMPLATE_SRC" "$HELPER_DEST"
  echo "  ✓ Scaffolded tests/e2e/helpers/visual.ts"
fi

# Final validation: non-empty + required symbols present
if [[ ! -s "$HELPER_DEST" ]]; then
  echo "ERROR: tests/e2e/helpers/visual.ts is empty after scaffold" >&2
  exit 1
fi
for symbol in compareRegression compareDesign; do
  if ! grep -q "$symbol" "$HELPER_DEST"; then
    echo "ERROR: tests/e2e/helpers/visual.ts missing export '$symbol'" >&2
    exit 1
  fi
done
echo "  ✓ tests/e2e/helpers/visual.ts validated"

# --- Handle missing package.json ---

if [[ ! -f "$PKG_JSON" ]]; then
  echo "  ! No package.json found — skipping dep install"
  echo "  ! Install manually: npm install -D $DEPS"
  # File-only mode: visual.ts is in place; exit 0 (VERSION will be bumped)
  exit 0
fi

# --- Detect package manager ---

PKG_MANAGER="unknown"
if [[ -f "$PROJECT_DIR/bun.lockb" ]] || [[ -f "$PROJECT_DIR/bun.lock" ]]; then
  PKG_MANAGER="bun"
elif [[ -f "$PROJECT_DIR/package-lock.json" ]]; then
  PKG_MANAGER="npm"
elif [[ -f "$PROJECT_DIR/yarn.lock" ]]; then
  PKG_MANAGER="yarn"
elif [[ -f "$PROJECT_DIR/pnpm-lock.yaml" ]]; then
  PKG_MANAGER="pnpm"
fi

# --- Install deps or check/warn ---

case "$PKG_MANAGER" in
  bun)
    if has_required_deps; then
      echo "  ✓ Deps found in devDependencies — skipping install"
    else
      echo "  ▸ Installing deps via bun..."
      (cd "$PROJECT_DIR" && bun add -d $DEPS)
      echo "  ✓ Deps installed via bun"
    fi
    ;;
  npm)
    if has_required_deps; then
      echo "  ✓ Deps found in devDependencies — skipping install"
    else
      echo "  ▸ Installing deps via npm..."
      (cd "$PROJECT_DIR" && npm install -D $DEPS)
      echo "  ✓ Deps installed via npm"
    fi
    ;;
  yarn|pnpm)
    # Check if deps were already installed manually before warning
    if has_required_deps; then
      echo "  ✓ Deps found in devDependencies — skipping install"
    else
      echo "  ! Package manager: $PKG_MANAGER — automatic install not supported"
      echo "  ! Install manually:"
      echo "    $PKG_MANAGER add -D $DEPS"
      echo "  ! Then re-run /spec.migrate to complete v3."
      exit 1
    fi
    ;;
  *)
    # No lock file detected: check if deps already present
    if has_required_deps; then
      echo "  ✓ Deps found in devDependencies — skipping install"
    else
      echo "  ! No package manager lock file found"
      echo "  ! Install manually:"
      echo "    npm install -D $DEPS"
      echo "  ! Then re-run /spec.migrate to complete v3."
      exit 1
    fi
    ;;
esac

# --- Exit criteria validation ---

# Verify the two runtime-critical deps. @types/* and pngjs are installed as part of DEPS
# but not individually checked — if bun/npm install exited 0, they were installed too.

# Check pixelmatch in devDependencies (run from PROJECT_DIR for relative require)
if ! (cd "$PROJECT_DIR" && node -e "const p=require('./package.json'); process.exit(p.devDependencies?.pixelmatch ? 0 : 1)"); then
  echo "ERROR: pixelmatch not found in devDependencies after install" >&2
  exit 1
fi
echo "  ✓ pixelmatch in devDependencies"

# Check sharp in devDependencies
if ! (cd "$PROJECT_DIR" && node -e "const p=require('./package.json'); process.exit(p.devDependencies?.sharp ? 0 : 1)"); then
  echo "ERROR: sharp not found in devDependencies after install" >&2
  exit 1
fi
echo "  ✓ sharp in devDependencies"

echo ""
echo "  Visual testing infrastructure ready."
echo "  Next: run /spec.test to capture visual baselines for your existing features."
echo ""

exit 0
