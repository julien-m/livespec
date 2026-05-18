#!/usr/bin/env bash
# @spec FR-009: Pre-commit / CI regression check — .specs/features/013-state-model-identity-resolution/spec.md#fr-009
#
# Fails the build if the literal placeholder "NNN-feature-name" reappears in
# command markdown, agent markdown, or generated .specs/features/<slug>/ artefacts.
#
# Allowed occurrences (scoped exclusions):
#   - .specs/features/013-state-model-identity-resolution/  (the spec defining the placeholder)
#   - system/templates/                                       (template files where the literal IS the variable)
#   - AUDIT.md, AUDIT-CODEX.md                                (consultative reports kept local; gitignored anyway)
#   - .git/, node_modules/, __pycache__/                      (irrelevant trees)
#   - This script itself                                      (mentions the literal in comments + grep pattern)

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PATTERN='NNN-feature-name'

EXCLUDES=(
  --exclude-dir=.git
  --exclude-dir=node_modules
  --exclude-dir=__pycache__
  --exclude-dir=013-state-model-identity-resolution
  --exclude-dir=templates
  --exclude=AUDIT.md
  --exclude=AUDIT-CODEX.md
  --exclude=check-no-placeholder.sh
)

# Search scope: commands/, agents/, .specs/features/, system/ (excluding templates and the
# defining spec). The placeholder remains valid in commands/spec-feature.md and other command
# markdown ONLY as a documented template variable — see system/identity.md for the convention.
# This check enforces that NO file in .specs/features/<other-slug>/ ever contains the literal,
# which would indicate that resolve_feature_slug was bypassed at runtime.

# Phase 1 — runtime state files: state files (pipeline.md, progress.md, ship.md, preflight.md)
# and execution logs (logs/*.md) are runtime-generated and MUST contain the resolved slug,
# never the placeholder. Hand-written documentation (spec.md, plan.md, changelog.md, etc.)
# may legitimately reference the literal as a template variable.
HITS=""
for fname in pipeline.md progress.md ship.md preflight.md preflight-report.md; do
  HITS+=$(grep -rn "${EXCLUDES[@]}" --include="$fname" "$PATTERN" .specs/ 2>/dev/null || true)
done
HITS+=$(grep -rn "${EXCLUDES[@]}" --include="*.md" "$PATTERN" .specs/features/*/logs/ 2>/dev/null || true)

if [ -n "$HITS" ]; then
  echo "FAIL: literal '$PATTERN' found in runtime state files / logs:" >&2
  echo "$HITS" >&2
  echo >&2
  echo "This indicates that resolve_feature_slug was bypassed at runtime." >&2
  echo "See system/identity.md for the resolution contract." >&2
  exit 1
fi

echo "OK: no '$PATTERN' literal in runtime state files or execution logs."
echo "(Occurrences in commands/, agents/, system/identity.md, spec.md/plan.md remain valid as documented template variables — see system/identity.md.)"
