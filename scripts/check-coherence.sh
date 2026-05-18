#!/usr/bin/env bash
set -euo pipefail

# LiveSpec — Internal coherence checker.
# Delegates command-surface consistency to the deterministic command audit.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$SCRIPT_DIR")"

echo "LiveSpec Coherence Check"
echo ""

python3 -m validator.cli command-audit --repo "$ROOT" --naming-policy hyphenated

echo ""
echo "All checks passed."
