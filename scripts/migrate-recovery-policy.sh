#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="${1:?Usage: migrate-recovery-policy.sh <project-dir> <livespec-dir>}"
LIVESPEC_DIR="${2:?Usage: migrate-recovery-policy.sh <project-dir> <livespec-dir>}"
POLICY="$PROJECT_DIR/.specs/recovery-policy.yaml"

# Existing policy bytes belong to the project and remain authoritative.
if [[ ! -e "$POLICY" && ! -L "$POLICY" ]]; then
  cp "$LIVESPEC_DIR/templates/recovery/recovery-policy.yaml" "$POLICY"
fi
