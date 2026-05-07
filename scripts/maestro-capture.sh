#!/usr/bin/env bash
# maestro-capture.sh — Capture screenshots from an Android emulator via adb.
#
# Wraps the adb screencap pipeline used by the Maestro runner as a convenience
# script for CI or direct CLI invocation.
#
# @spec FR-004: adb fallback screenshot — .specs/features/031-ui-runner-android/spec.md#fr-004
#
# Usage:
#   scripts/maestro-capture.sh <output-path> [emulator-serial]
#
# Arguments:
#   output-path     Local path where the PNG will be saved (required)
#   emulator-serial ADB serial of target emulator (optional; auto-detected)
#
# Environment:
#   ANDROID_HOME or ANDROID_SDK_ROOT   Path to Android SDK (required for adb)
#
# Examples:
#   scripts/maestro-capture.sh .specs/design/screens/home.png
#   scripts/maestro-capture.sh .specs/design/screens/home.png emulator-5554
#
# Exit codes:
#   0  Screenshot captured successfully
#   1  adb not found, emulator not running, or capture failed

set -euo pipefail

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REMOTE_SCREENSHOT_PATH="/sdcard/livespec_screen.png"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

log_info()  { echo "[maestro-capture] INFO:  $*" >&2; }
log_error() { echo "[maestro-capture] ERROR: $*" >&2; }

# ---------------------------------------------------------------------------
# Parse arguments
# ---------------------------------------------------------------------------

if [[ $# -lt 1 ]]; then
    echo "Usage: $0 <output-path> [emulator-serial]" >&2
    echo "Example: $0 .specs/design/screens/home.png emulator-5554" >&2
    exit 1
fi

OUTPUT_PATH="$1"
EMULATOR_SERIAL="${2:-}"

# ---------------------------------------------------------------------------
# Verify Android SDK / adb availability
# ---------------------------------------------------------------------------

if [[ -z "${ANDROID_HOME:-}" && -z "${ANDROID_SDK_ROOT:-}" ]]; then
    log_error "Android SDK not configured."
    log_error "Set ANDROID_HOME or ANDROID_SDK_ROOT to your SDK path."
    log_error "Install: https://developer.android.com/studio"
    exit 1
fi

ADB_PATH="$(command -v adb 2>/dev/null || true)"
if [[ -z "$ADB_PATH" ]]; then
    SDK_ROOT="${ANDROID_HOME:-${ANDROID_SDK_ROOT}}"
    ADB_PATH="${SDK_ROOT}/platform-tools/adb"
    if [[ ! -x "$ADB_PATH" ]]; then
        log_error "adb not found on PATH or in Android SDK platform-tools."
        log_error "Ensure Android SDK platform-tools are installed:"
        log_error "  sdkmanager 'platform-tools'"
        exit 1
    fi
fi

log_info "Using adb: $ADB_PATH"

# ---------------------------------------------------------------------------
# Detect running emulator if serial not provided
# ---------------------------------------------------------------------------

if [[ -z "$EMULATOR_SERIAL" ]]; then
    # Pick the first running emulator
    EMULATOR_SERIAL="$(
        "$ADB_PATH" devices 2>/dev/null \
            | awk '/^emulator-[0-9]+\s+device/{print $1; exit}'
    )"
    if [[ -z "$EMULATOR_SERIAL" ]]; then
        log_error "No running Android emulator detected."
        log_error "Start an emulator first: emulator -avd Pixel_8_API_35 -no-window &"
        log_error "Then check: adb devices"
        exit 1
    fi
    log_info "Auto-detected emulator: $EMULATOR_SERIAL"
else
    log_info "Using specified emulator: $EMULATOR_SERIAL"
fi

# Verify the serial is connected
DEVICE_STATE="$(
    "$ADB_PATH" -s "$EMULATOR_SERIAL" get-state 2>/dev/null || true
)"
if [[ "$DEVICE_STATE" != "device" ]]; then
    log_error "Emulator $EMULATOR_SERIAL is not in 'device' state (got: ${DEVICE_STATE:-offline})."
    log_error "Check: adb devices"
    exit 1
fi

# ---------------------------------------------------------------------------
# Capture screenshot on device
# ---------------------------------------------------------------------------

log_info "Capturing screenshot on $EMULATOR_SERIAL → $REMOTE_SCREENSHOT_PATH"

if ! "$ADB_PATH" -s "$EMULATOR_SERIAL" \
        shell screencap -p "$REMOTE_SCREENSHOT_PATH" 2>/dev/null; then
    log_error "adb screencap failed on $EMULATOR_SERIAL."
    log_error "Ensure the emulator is fully booted and responsive."
    exit 1
fi

# ---------------------------------------------------------------------------
# Pull PNG to local output path
# ---------------------------------------------------------------------------

OUTPUT_DIR="$(dirname "$OUTPUT_PATH")"
if [[ -n "$OUTPUT_DIR" && "$OUTPUT_DIR" != "." ]]; then
    mkdir -p "$OUTPUT_DIR"
fi

log_info "Pulling screenshot → $OUTPUT_PATH"

if ! "$ADB_PATH" -s "$EMULATOR_SERIAL" \
        pull "$REMOTE_SCREENSHOT_PATH" "$OUTPUT_PATH" 2>/dev/null; then
    log_error "adb pull failed. Could not retrieve $REMOTE_SCREENSHOT_PATH from $EMULATOR_SERIAL."
    exit 1
fi

# ---------------------------------------------------------------------------
# Detect JPEG vs PNG and convert if needed
# ---------------------------------------------------------------------------

# Some older API levels write JPEG via screencap even with -p flag
# Check magic bytes: PNG starts with 0x89 0x50 (‰P)
MAGIC="$(xxd -l 2 -p "$OUTPUT_PATH" 2>/dev/null || true)"
if [[ "$MAGIC" == "ffd8" ]]; then
    # JPEG detected — convert to PNG using ffmpeg if available, else sips
    CONVERTED_PATH="${OUTPUT_PATH%.jpg}.png"
    CONVERTED_PATH="${CONVERTED_PATH%.jpeg}.png"
    log_info "JPEG output detected — converting to PNG at $CONVERTED_PATH"
    if command -v ffmpeg &>/dev/null; then
        if ffmpeg -y -i "$OUTPUT_PATH" "$CONVERTED_PATH" 2>/dev/null; then
            mv -f "$CONVERTED_PATH" "$OUTPUT_PATH"
            log_info "Converted JPEG → PNG via ffmpeg"
        else
            log_error "ffmpeg JPEG→PNG conversion failed. Keeping original JPEG."
        fi
    elif command -v sips &>/dev/null; then
        if sips -s format png "$OUTPUT_PATH" --out "$CONVERTED_PATH" 2>/dev/null; then
            mv -f "$CONVERTED_PATH" "$OUTPUT_PATH"
            log_info "Converted JPEG → PNG via sips"
        else
            log_error "sips JPEG→PNG conversion failed. Keeping original JPEG."
        fi
    else
        log_error "Neither ffmpeg nor sips available for JPEG→PNG conversion."
        log_error "Install ffmpeg: brew install ffmpeg"
    fi
fi

# ---------------------------------------------------------------------------
# Clean up remote screenshot
# ---------------------------------------------------------------------------

"$ADB_PATH" -s "$EMULATOR_SERIAL" shell rm -f "$REMOTE_SCREENSHOT_PATH" 2>/dev/null || true

# ---------------------------------------------------------------------------
# Verify output
# ---------------------------------------------------------------------------

if [[ ! -f "$OUTPUT_PATH" ]]; then
    log_error "Output file not found after capture: $OUTPUT_PATH"
    exit 1
fi

FILE_SIZE="$(wc -c < "$OUTPUT_PATH" 2>/dev/null || echo 0)"
if [[ "$FILE_SIZE" -lt 100 ]]; then
    log_error "Output file appears empty or corrupted: $OUTPUT_PATH ($FILE_SIZE bytes)"
    exit 1
fi

log_info "Screenshot saved: $OUTPUT_PATH (${FILE_SIZE} bytes)"
exit 0
