#!/usr/bin/env bash
# LiveSpec traceability anchors
# @spec(FR-002)
# @spec(FR-003)

# xcuitest-capture.sh — Capture screenshots from XCUITest run on iOS/watchOS simulator.
#
# @spec FR-002: .xcresult parsing + HEIC→PNG — .specs/features/030-ui-runner-ios-watchos/spec.md#fr-002
# @spec FR-003: simulator boot orchestration — .specs/features/030-ui-runner-ios-watchos/spec.md#fr-003
#
# Usage:
#   xcuitest-capture.sh <simulator-udid> <test-scheme> <output-dir> [ios|watchos]
#
# Arguments:
#   simulator-udid   UDID of the target simulator (from xcrun simctl list devices)
#   test-scheme      Xcode test scheme name
#   output-dir       Directory where PNG screenshots are written
#   platform         ios (default) or watchos
#
# Exit codes:
#   0 — success
#   1 — general error (missing Xcode, no .xcresult produced)
#   2 — Xcode license not accepted

set -euo pipefail

SIMULATOR_UDID="${1:?Usage: xcuitest-capture.sh <udid> <scheme> <output-dir> [ios|watchos]}"
TEST_SCHEME="${2:?Usage: xcuitest-capture.sh <udid> <scheme> <output-dir> [ios|watchos]}"
OUTPUT_DIR="${3:?Usage: xcuitest-capture.sh <udid> <scheme> <output-dir> [ios|watchos]}"
PLATFORM="${4:-ios}"

mkdir -p "$OUTPUT_DIR"

# ── Platform check ─────────────────────────────────────────────────────────────
if [[ "$(uname)" != "Darwin" ]]; then
  echo "ERROR: iOS UI runner requires macOS — skipped on non-macOS hosts" >&2
  exit 0
fi

# ── Toolchain check ───────────────────────────────────────────────────────────
if ! xcrun --find xcodebuild > /dev/null 2>&1; then
  echo "ERROR: Xcode not installed. Install from App Store or https://developer.apple.com/xcode/" >&2
  exit 1
fi

# ── License check ─────────────────────────────────────────────────────────────
if xcodebuild -license check 2>&1 | grep -qi "not been accepted"; then
  echo "ERROR: Xcode license not accepted. Run: sudo xcodebuild -license accept" >&2
  exit 2
fi

# ── Simulator boot ────────────────────────────────────────────────────────────
# @spec FR-003: simulator boot orchestration — .specs/features/030-ui-runner-ios-watchos/spec.md#fr-003
SIM_STATE=$(xcrun simctl list devices --json | python3 -c "
import sys, json
data = json.load(sys.stdin)
udid = '${SIMULATOR_UDID}'
for runtime_devs in data.get('devices', {}).values():
    for dev in runtime_devs:
        if dev.get('udid') == udid:
            print(dev.get('state', 'Unknown'))
            sys.exit(0)
print('NotFound')
" 2>/dev/null || echo "Unknown")

if [[ "$SIM_STATE" == "NotFound" ]]; then
  echo "ERROR: Simulator $SIMULATOR_UDID not found. Run: xcrun simctl list devices" >&2
  exit 1
fi

if [[ "$SIM_STATE" != "Booted" ]]; then
  echo "[xcuitest-capture] Booting simulator $SIMULATOR_UDID..."
  xcrun simctl boot "$SIMULATOR_UDID" 2>/dev/null || true
  # Wait for ready
  if ! xcrun simctl bootstatus "$SIMULATOR_UDID" -b 2>/dev/null; then
    echo "WARNING: Simulator may not be fully ready — proceeding anyway" >&2
  fi
fi

# ── Destination string ────────────────────────────────────────────────────────
if [[ "$PLATFORM" == "watchos" ]]; then
  DESTINATION="platform=watchOS Simulator,id=$SIMULATOR_UDID"
else
  DESTINATION="platform=iOS Simulator,id=$SIMULATOR_UDID"
fi

# ── Run xcodebuild test ───────────────────────────────────────────────────────
XCRESULT_DIR=$(mktemp -d)
XCRESULT_BUNDLE="$XCRESULT_DIR/result.xcresult"

echo "[xcuitest-capture] Running xcodebuild test -scheme '$TEST_SCHEME' -destination '$DESTINATION'"

# @spec FR-002: run xcodebuild and produce .xcresult — .specs/features/030-ui-runner-ios-watchos/spec.md#fr-002
xcodebuild test \
  -scheme "$TEST_SCHEME" \
  -destination "$DESTINATION" \
  -resultBundlePath "$XCRESULT_BUNDLE" \
  CODE_SIGN_IDENTITY="" \
  CODE_SIGNING_REQUIRED=NO \
  2>&1 || {
  EXIT_CODE=$?
  # Check for license error in output
  if xcodebuild -license check 2>&1 | grep -qi "not been accepted"; then
    echo "ERROR: Xcode license not accepted. Run: sudo xcodebuild -license accept" >&2
    rm -rf "$XCRESULT_DIR"
    exit 2
  fi
  echo "WARNING: xcodebuild exited $EXIT_CODE — attempting screenshot extraction from partial .xcresult" >&2
}

if [[ ! -d "$XCRESULT_BUNDLE" ]]; then
  echo "ERROR: No .xcresult bundle produced at $XCRESULT_BUNDLE" >&2
  rm -rf "$XCRESULT_DIR"
  exit 1
fi

# ── Extract screenshots from .xcresult ────────────────────────────────────────
echo "[xcuitest-capture] Extracting screenshots from $XCRESULT_BUNDLE"

# @spec FR-002: xcresulttool extraction + HEIC→PNG — .specs/features/030-ui-runner-ios-watchos/spec.md#fr-002
python3 - "$XCRESULT_BUNDLE" "$OUTPUT_DIR" <<'PYEOF'
import sys
import json
import subprocess
import pathlib
import shutil
import tempfile

bundle = sys.argv[1]
outdir = sys.argv[2]
pathlib.Path(outdir).mkdir(parents=True, exist_ok=True)

# Get JSON manifest from xcresulttool
try:
    result = subprocess.run(
        ["xcrun", "xcresulttool", "get", "--path", bundle, "--format", "json"],
        capture_output=True, text=True, timeout=60, check=False
    )
    data = json.loads(result.stdout or "{}")
except Exception as e:
    print(f"WARNING: Failed to parse .xcresult manifest: {e}", file=sys.stderr)
    sys.exit(0)

def extract_attachments(node, found=None):
    """Recursively find ActionTestAttachment nodes."""
    if found is None:
        found = []
    if isinstance(node, dict):
        if node.get("_type", {}).get("_name") == "ActionTestAttachment":
            found.append(node)
        for v in node.values():
            extract_attachments(v, found)
    elif isinstance(node, list):
        for item in node:
            extract_attachments(item, found)
    return found

attachments = extract_attachments(data)
exported = 0

for i, att in enumerate(attachments):
    name_val = att.get("name", {})
    name = name_val.get("_value", f"screenshot_{i}") if isinstance(name_val, dict) else f"screenshot_{i}"
    payload_id_container = att.get("payloadRef", {})
    payload_ref = payload_id_container.get("id", {}).get("_value") if isinstance(payload_id_container, dict) else None
    if not payload_ref:
        continue

    try:
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(
                ["xcrun", "xcresulttool", "export",
                 "--path", bundle,
                 "--id", payload_ref,
                 "--output-path", tmp,
                 "--type", "file"],
                capture_output=True, text=True, timeout=30, check=False
            )
            for f in pathlib.Path(tmp).iterdir():
                suffix = f.suffix.lower()
                if suffix not in (".heic", ".png", ".jpg", ".jpeg"):
                    continue
                png_dest = pathlib.Path(outdir) / f"{name}.png"
                if suffix == ".heic":
                    # Convert HEIC → PNG using macOS sips
                    r = subprocess.run(
                        ["sips", "-s", "format", "png", str(f), "--out", str(png_dest)],
                        capture_output=True, check=False
                    )
                    if r.returncode == 0 and png_dest.exists():
                        exported += 1
                else:
                    shutil.copy2(f, png_dest)
                    exported += 1
    except Exception as e:
        print(f"WARNING: Could not export attachment '{name}': {e}", file=sys.stderr)
        continue

print(f"[xcuitest-capture] Exported {exported} screenshot(s) to {outdir}")
PYEOF

rm -rf "$XCRESULT_DIR"
echo "[xcuitest-capture] Done. Screenshots in $OUTPUT_DIR"
