#!/usr/bin/env bash
# LiveSpec traceability anchors
# @spec(FR-008)

# audit-antidrift-coverage.sh — verify that every canonical LiveSpec command
# imports `system/anti-drift-block.md`.
#
# The anti-drift block carries the runtime "hook & integration resolution"
# directive (Phase 5.9 of plan-C.md). Any command missing the @import
# directive would silently bypass `livespec hooks resolve`, breaking the
# Level 0 integration pattern and creating a coverage gap.
#
# This script is the AC-13 + Phase 9.2 regression check. Empty stdout +
# exit code 0 = coverage is complete (20/20 commands on `main` at the
# time of merging this feature).
#
# Usage: scripts/audit-antidrift-coverage.sh
set -euo pipefail

cd "$(dirname "$0")/.."

missing=0
while IFS= read -r n; do
    [ -n "$n" ] || continue
    grep -qF "@import system/anti-drift-block.md" ".agent-sync/skills/$n/SKILL.md" \
      || { echo "MISSING: .agent-sync/skills/$n/SKILL.md"; missing=1; }
done < <(python3 -c "from validator.integrations import valid_command_names; print('\n'.join(sorted(valid_command_names())))")

exit "$missing"
