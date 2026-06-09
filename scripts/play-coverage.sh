#!/usr/bin/env bash
# LiveSpec traceability anchors
# @spec(FR-008)

set -euo pipefail

# LiveSpec — build spec coverage playground data.
# Usage: bash scripts/play-coverage.sh <feature-name> <source-dir> [--no-open]

FEATURE="${1:?Usage: play-coverage.sh <feature-name> <source-dir> [--no-open]}"
SOURCE_DIR="${2:?Usage: play-coverage.sh <feature-name> <source-dir> [--no-open]}"
NO_OPEN="${3:-}"

ARGS=(play-coverage --feature "$FEATURE" --source-dir "$SOURCE_DIR")
if [[ "$NO_OPEN" == "--no-open" ]]; then
  ARGS+=(--no-open)
fi

python3 -m validator.cli "${ARGS[@]}"
