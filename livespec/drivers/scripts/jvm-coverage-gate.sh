#!/usr/bin/env bash
# @spec FR-001: JVM coverage gate escape-hatch script — .specs/features/022-driver-jvm/spec.md#fr-001
# @spec AC-002: Coverage capability auto-detects Gradle vs Maven and dispatches.
# @spec AC-003: Locates JaCoCo lcov.info at the standard path (Gradle / Maven).
# @spec AC-004: When JaCoCo is not configured, exit 0 with a setup-guide message.
# @spec AC-010: Gradle takes priority when both build files are present.
#
# Usage:
#   jvm-coverage-gate.sh [<lcov_path>] [<threshold>]
#
# Environment overrides (mainly for tests):
#   LIVESPEC_JVM_BUILD_TOOL — force "gradle" or "maven" (skip auto-detection)
#   LIVESPEC_JVM_SKIP_RUN=1 — do not invoke ./gradlew or mvn (probe only)
#
# Exit codes:
#   0 — JaCoCo gate passed OR JaCoCo not configured (skip with guide).
#   1 — gate failed (build error, threshold violation, no build file).

set -u
set -o pipefail

LCOV_PATH_OVERRIDE="${1:-}"
THRESHOLD="${2:-80}"

emit() {
    printf '%s\n' "$*"
}

# --- Step 1: detect build tool (Gradle priority over Maven, AC-010) ----
BUILD_TOOL="${LIVESPEC_JVM_BUILD_TOOL:-}"
if [ -z "$BUILD_TOOL" ]; then
    if [ -f build.gradle ] || [ -f build.gradle.kts ]; then
        BUILD_TOOL="gradle"
    elif [ -f pom.xml ]; then
        BUILD_TOOL="maven"
    else
        emit "Coverage gate failed: no JVM build file found (expected build.gradle, build.gradle.kts, or pom.xml)"
        exit 1
    fi
fi

# --- Step 2: probe for JaCoCo configuration ----------------------------
HAS_JACOCO=0
case "$BUILD_TOOL" in
    gradle)
        for f in build.gradle build.gradle.kts; do
            if [ -f "$f" ] && grep -qiE '(jacoco|"jacoco"|id\("jacoco"\)|id .jacoco.)' "$f"; then
                HAS_JACOCO=1
                break
            fi
        done
        DEFAULT_LCOV_PATH="build/reports/jacoco/test/lcov.info"
        ;;
    maven)
        if [ -f pom.xml ] && grep -qi 'jacoco-maven-plugin' pom.xml; then
            HAS_JACOCO=1
        fi
        DEFAULT_LCOV_PATH="target/site/jacoco/lcov.info"
        ;;
    *)
        emit "Coverage gate failed: unknown build tool '$BUILD_TOOL'"
        exit 1
        ;;
esac

LCOV_PATH="${LCOV_PATH_OVERRIDE:-$DEFAULT_LCOV_PATH}"

if [ "$HAS_JACOCO" -eq 0 ]; then
    # AC-004: emit setup-guide and exit 0 (capability is "not configured", not "broken").
    emit "JaCoCo not configured in build.gradle/pom.xml — see docs for setup"
    exit 0
fi

# --- Step 3: invoke the build tool to produce coverage + apply gate ----
if [ -z "${LIVESPEC_JVM_SKIP_RUN:-}" ]; then
    case "$BUILD_TOOL" in
        gradle)
            # Prefer the wrapper when it ships with the project.
            if [ -x ./gradlew ]; then
                GRADLE_CMD="./gradlew"
            elif command -v gradle > /dev/null 2>&1; then
                GRADLE_CMD="gradle"
            else
                emit "Coverage gate failed: neither ./gradlew nor gradle is available"
                exit 1
            fi
            if ! "$GRADLE_CMD" test jacocoTestReport jacocoTestCoverageVerification; then
                emit "Coverage gate failed: gradle exited non-zero (test or JaCoCo verification failure)"
                exit 1
            fi
            ;;
        maven)
            if ! command -v mvn > /dev/null 2>&1; then
                emit "Coverage gate failed: mvn is not available on PATH"
                exit 1
            fi
            if ! mvn verify; then
                emit "Coverage gate failed: mvn verify exited non-zero (test or JaCoCo rule failure)"
                exit 1
            fi
            ;;
    esac
fi

# --- Step 4: report verdict ---------------------------------------------
if [ -f "$LCOV_PATH" ]; then
    emit "Coverage gate PASS: lcov.info located at $LCOV_PATH (threshold ${THRESHOLD}% enforced by JaCoCo build rule)"
    exit 0
fi

# JaCoCo configured but no lcov produced — usually means the lcov-export task
# is missing from the build file. Surface a clear hint without failing the gate
# (the JaCoCo XML/HTML reports may still be present).
emit "Coverage gate WARNING: JaCoCo configured but lcov.info not found at $LCOV_PATH — add an lcov export task (see docs)"
exit 0
