#!/usr/bin/env bash
set -euo pipefail

# LiveSpec — Open Spec Coverage playground with grep data
# Usage: bash scripts/play-coverage.sh <feature-name> <source-dir>
# Example: bash scripts/play-coverage.sh 001-import-and-preview-html-artifacts app/

FEATURE="${1:?Usage: play-coverage.sh <feature-name> <source-dir>}"
SOURCE_DIR="${2:?Usage: play-coverage.sh <feature-name> <source-dir>}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLAYGROUND="$SCRIPT_DIR/../playground/spec-coverage.html"

if [[ ! -f "$PLAYGROUND" ]]; then
  echo "ERROR: Playground not found at $PLAYGROUND" >&2
  exit 1
fi

# Resolve to absolute path
PLAYGROUND="$(cd "$(dirname "$PLAYGROUND")" && pwd)/$(basename "$PLAYGROUND")"

# Run grep
GREP_OUTPUT=$(grep -rn "@spec FR-" "$SOURCE_DIR" 2>/dev/null || true)

if [[ -z "$GREP_OUTPUT" ]]; then
  echo "No @spec anchors found in $SOURCE_DIR" >&2
  ANCHOR_COUNT=0
  FILE_COUNT=0
else
  ANCHOR_COUNT=$(echo "$GREP_OUTPUT" | wc -l | tr -d ' ')
  FILE_COUNT=$(echo "$GREP_OUTPUT" | cut -d: -f1 | sort -u | wc -l | tr -d ' ')
fi

# Build base64-encoded JSON payload via python3
B64=$(python3 -c "
import json, base64, sys
data = json.dumps({
    'grep': sys.stdin.read(),
    'feature': '$FEATURE',
    'sourceDir': '$SOURCE_DIR'
})
sys.stdout.write(base64.b64encode(data.encode()).decode())
" <<< "$GREP_OUTPUT")

# macOS `open` strips hash fragments from file:// URLs.
# Workaround: create a temp HTML that redirects with the fragment intact.
REDIRECT="/tmp/livespec-redirect-$$.html"
cat > "$REDIRECT" << EOF
<!DOCTYPE html><html><body><script>
window.location.href = "file://$PLAYGROUND#data=$B64";
</script></body></html>
EOF
open "$REDIRECT"
# Clean up after a short delay (browser has time to load the redirect)
(sleep 3 && rm -f "$REDIRECT") &

echo "Spec Coverage playground opened."
echo ""
echo "  Feature:    $FEATURE"
echo "  Source dir:  $SOURCE_DIR"
echo "  @spec anchors found: $ANCHOR_COUNT across $FILE_COUNT files"
echo ""
echo "Load .specs project in the sidebar to view full spec-to-code traceability."
