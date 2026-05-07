#!/usr/bin/env bash
# @spec FR-002: Go coverage gate escape-hatch script — .specs/features/020-driver-go/spec.md#fr-002
# @spec AC-002: Gate runs `go test -coverprofile` and converts to lcov.
# @spec AC-003: Gate applies threshold and exits 0/1.
# @spec AC-007: Script accepts coverprofile path + threshold, writes lcov.info, exits 0/1.
# @spec EC-002: Empty coverprofile -> "No coverage data — add tests" + exit 1.
# @spec EC-004: lcov conversion is implemented inline (no external gocov tool required).
#
# Usage:
#   go-coverage-gate.sh [<coverprofile_path>] [<lcov_path>] [<threshold>]
#
# Environment overrides (mainly for tests / pre-existing data):
#   LIVESPEC_GATE_COVERPROFILE — read coverage from this coverprofile path directly,
#                                do NOT run `go test`.
#   LIVESPEC_SKIP_RUN=1        — skip the `go test` invocation but still convert
#                                pre-existing coverprofile output.
#   CGO_ENABLED                 — passthrough to `go test`. Users may set
#                                CGO_ENABLED=0 to silence CGO toolchain
#                                requirements (spec EC-003).
#
# Exit codes:
#   0 — coverage >= threshold.
#   1 — coverage < threshold OR no coverage data OR no Go module.

set -u
set -o pipefail

COVERPROFILE_PATH="${1:-coverage.out}"
LCOV_PATH="${2:-coverage/lcov.info}"
# Default to the spec threshold (70) so callers can omit the arg and still enforce AC-003.
THRESHOLD="${3:-70}"

emit() {
    printf '%s\n' "$*"
}

# --- Step 1: detect Go module layout ------------------------------------
if [ ! -f go.mod ]; then
    emit "Coverage gate failed: no go.mod found"
    exit 1
fi

# --- Step 2: obtain coverprofile data -----------------------------------
SOURCE_PROFILE="${LIVESPEC_GATE_COVERPROFILE:-}"
if [ -n "$SOURCE_PROFILE" ]; then
    if [ ! -f "$SOURCE_PROFILE" ]; then
        emit "Coverage data not generated — check for test crashes (missing $SOURCE_PROFILE)"
        exit 1
    fi
    PROFILE_FILE="$SOURCE_PROFILE"
else
    if [ -z "${LIVESPEC_SKIP_RUN:-}" ]; then
        # The driver contract is a zero exit with fresh coverprofile artifacts;
        # any non-zero `go test` is a hard gate failure (compile or test failure).
        if ! go test -coverprofile="$COVERPROFILE_PATH" ./...; then
            emit "Coverage gate failed: go test exited non-zero"
            exit 1
        fi
    fi

    if [ ! -f "$COVERPROFILE_PATH" ]; then
        emit "Coverage data not generated — check for test crashes (missing $COVERPROFILE_PATH)"
        exit 1
    fi
    PROFILE_FILE="$COVERPROFILE_PATH"
fi

# --- Step 3: validate the coverprofile is non-trivial -------------------
# A Go coverprofile always starts with `mode: set|count|atomic`. A file that
# contains only that header means there were no test files exercised (EC-002).
PROFILE_LINES=$(wc -l < "$PROFILE_FILE" | tr -d ' ')
if [ "$PROFILE_LINES" -le 1 ]; then
    emit "No coverage data — add tests (coverprofile $PROFILE_FILE has no entries)"
    exit 1
fi

# --- Step 4: compute coverage percent ----------------------------------
# Prefer `go tool cover -func` for the canonical total; fall back to inline
# parsing of the coverprofile when the toolchain is unavailable (EC-004).
PCT=""
if command -v go > /dev/null 2>&1; then
    if FUNC_OUTPUT="$(go tool cover -func="$PROFILE_FILE" 2>/dev/null)"; then
        # The last line is `total: (statements) NN.N%`.
        TOTAL_LINE="$(printf '%s\n' "$FUNC_OUTPUT" | awk '/^total:/ {print $NF}')"
        if [ -n "$TOTAL_LINE" ]; then
            # Strip trailing % and the decimal portion to keep an integer (matches
            # the swift gate's int-percent contract; bc is not available here).
            PCT="${TOTAL_LINE%%.*}"
            PCT="${PCT%\%}"
        fi
    fi
fi

if [ -z "$PCT" ]; then
    # EC-004 fallback: parse the coverprofile directly. Each non-header line is:
    #   <file>:<from>.<col>,<to>.<col> <num_stmts> <count>
    # Aggregate statements vs covered statements.
    PCT="$(awk '
        NR == 1 && /^mode:/ { next }
        NF >= 3 {
            stmts = $(NF-1) + 0
            count = $NF + 0
            total += stmts
            if (count > 0) {
                hit += stmts
            }
        }
        END {
            if (total == 0) { print ""; exit }
            printf "%d", (hit * 100) / total
        }
    ' "$PROFILE_FILE")"
fi

if [ -z "$PCT" ]; then
    emit "No coverage data — add tests (coverprofile $PROFILE_FILE has no entries)"
    exit 1
fi

# --- Step 5: convert coverprofile -> lcov.info -------------------------
mkdir -p "$(dirname "$LCOV_PATH")"

# Inline coverprofile->lcov conversion (EC-004): emit DA: lines for each
# statement range, grouped by source file. Multiple ranges sharing a starting
# line are summed so the lcov reader sees one DA: per source line.
awk '
    NR == 1 && /^mode:/ { next }
    NF >= 3 {
        # Field 1: <file>:<from>.<col>,<to>.<col>
        n = split($1, parts, ":")
        if (n < 2) { next }
        # Rebuild the file path so Windows-style paths with drive letters are
        # preserved (last segment is always the line.col,line.col range).
        file = parts[1]
        for (i = 2; i < n; i++) {
            file = file ":" parts[i]
        }
        range = parts[n]
        split(range, fromto, ",")
        split(fromto[1], from, ".")
        line = from[1] + 0
        count = $NF + 0

        if (!(file in file_seen)) {
            file_seen[file] = ++file_idx
            file_order[file_idx] = file
        }
        key = file SUBSEP line
        if (!(key in line_count)) {
            line_count_per_file[file] += 1
            line_order[file SUBSEP line_count_per_file[file]] = line
        }
        line_count[key] += count
    }
    END {
        for (fi = 1; fi <= file_idx; fi++) {
            f = file_order[fi]
            print "TN:"
            print "SF:" f
            nlines = line_count_per_file[f] + 0
            for (j = 1; j <= nlines; j++) {
                l = line_order[f SUBSEP j]
                c = line_count[f SUBSEP l]
                printf "DA:%d,%d\n", l, c
            }
            print "end_of_record"
        }
    }
' "$PROFILE_FILE" > "$LCOV_PATH"

# --- Step 6: gate verdict ----------------------------------------------
if [ "$PCT" -ge "$THRESHOLD" ]; then
    emit "Coverage gate PASS: ${PCT}% >= ${THRESHOLD}%"
    exit 0
fi

emit "Coverage gate failed: ${PCT}% < ${THRESHOLD}%"
exit 1
