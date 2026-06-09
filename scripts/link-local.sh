#!/usr/bin/env bash
# LiveSpec traceability anchors
# @spec(FR-003)
# @spec(FR-005)

set -euo pipefail

# Backward-compatible entry point. Provider-native Claude/Codex assets are now
# generated through cc-hub from `.agent-sync`; this script no longer writes
# `.claude/commands` or `.claude/agents` symlinks directly.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$SCRIPT_DIR/sync-agent-assets.sh" "$@"
