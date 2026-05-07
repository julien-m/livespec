#!/usr/bin/env bash
# @spec FR-002: Swift coverage gate escape-hatch script — .specs/features/019-driver-swift/spec.md#fr-002
# @spec AC-003: Gate script parses lcov, computes line %, exits 0/1 vs threshold.
# @spec AC-004: Xcode-only project (no Package.swift) -> graceful exit 0 with hint.
# @spec EC-005: Linux fallback uses llvm-cov directly when xcrun is unavailable.
#
# Usage:
#   swift-coverage-gate.sh <lcov_path> [<threshold>]
#
# Environment overrides (mainly for tests / pre-existing data):
#   LIVESPEC_GATE_LCOV     — read coverage from this lcov path directly, do NOT run swift test.
#   LIVESPEC_SKIP_RUN=1    — skip the swift test invocation but still try to export lcov.
#
# Exit codes:
#   0 — coverage >= threshold OR Xcode-only graceful skip.
#   1 — coverage < threshold OR no coverage data available OR no Swift project.

set -u
set -o pipefail

LCOV_PATH="${1:-.build/coverage/lcov.info}"
# Default to the spec threshold so callers can omit the arg and still enforce AC-003 consistently.
THRESHOLD="${2:-75}"

emit() {
    printf '%s\n' "$*"
}

# --- Step 1: detect Swift project layout ---------------------------------
if [ ! -f Package.swift ]; then
    # Bash-only glob probing is intentional here because we need a cheap top-level Xcode marker without traversing the tree.
    if compgen -G "*.xcodeproj" > /dev/null 2>&1; then
        emit "Xcode project detected. Use xcodebuild for coverage. See livespec/drivers/swift.yaml for configuration."
        exit 0
    fi
    emit "Coverage gate failed: no Package.swift or .xcodeproj found"
    exit 1
fi

# --- Step 2: obtain lcov data -------------------------------------------
SOURCE_LCOV="${LIVESPEC_GATE_LCOV:-}"
if [ -n "$SOURCE_LCOV" ]; then
    if [ ! -f "$SOURCE_LCOV" ]; then
        emit "Coverage data not generated — check for test crashes (missing $SOURCE_LCOV)"
        exit 1
    fi
    LCOV_FILE="$SOURCE_LCOV"
else
    if [ -z "${LIVESPEC_SKIP_RUN:-}" ]; then
        # The driver contract is a zero exit with fresh coverage artifacts in .build; any non-zero test run is a hard gate failure.
        if ! swift test --enable-code-coverage; then
            emit "Coverage gate failed: swift test exited non-zero"
            exit 1
        fi
    fi

    PROFDATA="$(find .build -name '*.profdata' -print -quit 2>/dev/null || true)"
    if [ -z "$PROFDATA" ]; then
        emit "Coverage data not generated — check for test crashes (no .profdata under .build)"
        exit 1
    fi

    BINARY="$(find .build -name '*.xctest' -print -quit 2>/dev/null || true)"
    if [ -z "$BINARY" ]; then
        BINARY="$(find .build -type f -perm -u+x -name '*PackageTests*' -print -quit 2>/dev/null || true)"
    fi
    if [ -z "$BINARY" ]; then
        emit "Coverage data not generated — could not locate test binary under .build"
        exit 1
    fi

    mkdir -p "$(dirname "$LCOV_PATH")"

    # macOS exposes llvm-cov via xcrun, while Linux packages it directly; both branches must emit lcov to LCOV_PATH or fail loudly.
    if command -v xcrun > /dev/null 2>&1; then
        if ! xcrun llvm-cov export -format=lcov -instr-profile "$PROFDATA" "$BINARY" > "$LCOV_PATH"; then
            emit "Coverage data not generated — xcrun llvm-cov export failed"
            exit 1
        fi
    elif command -v llvm-cov > /dev/null 2>&1; then
        if ! llvm-cov export -format=lcov -instr-profile "$PROFDATA" "$BINARY" > "$LCOV_PATH"; then
            emit "Coverage data not generated — llvm-cov export failed"
            exit 1
        fi
    else
        emit "xcrun not found — Swift coverage requires macOS (or llvm-cov on Linux)"
        exit 1
    fi
    LCOV_FILE="$LCOV_PATH"
fi

# --- Step 3: parse DA: lines and compute percent ------------------------
TOTAL=0
HIT=0
while IFS= read -r line; do
    case "$line" in
        DA:*)
            count="${line##*,}"
            TOTAL=$((TOTAL + 1))
            if [ "$count" != "0" ]; then
                HIT=$((HIT + 1))
            fi
            ;;
    esac
done < "$LCOV_FILE"

if [ "$TOTAL" -eq 0 ]; then
    emit "Coverage data not generated — lcov file contains no DA: entries ($LCOV_FILE)"
    exit 1
fi

# Integer percent (avoid bc dependency).
PCT=$(( (HIT * 100) / TOTAL ))

if [ "$PCT" -ge "$THRESHOLD" ]; then
    emit "Coverage gate PASS: ${PCT}% >= ${THRESHOLD}%"
    exit 0
fi

emit "Coverage gate failed: ${PCT}% < ${THRESHOLD}%"
exit 1
