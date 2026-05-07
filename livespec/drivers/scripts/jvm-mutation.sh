#!/usr/bin/env bash
# @spec AC-007: Mutation capability detects pitest plugin (Gradle or Maven).
# @spec AC-008: Mutation capability parses mutations.xml.
# — .specs/features/022-driver-jvm/spec.md#ac-007
#
# Environment overrides:
#   LIVESPEC_JVM_BUILD_TOOL  — force "gradle" or "maven"
#   LIVESPEC_JVM_SKIP_RUN=1  — probe only (do not invoke gradle/mvn)

set -u
set -o pipefail

emit() {
    printf '%s\n' "$*"
}

# --- detect build tool --------------------------------------------------
BUILD_TOOL="${LIVESPEC_JVM_BUILD_TOOL:-}"
if [ -z "$BUILD_TOOL" ]; then
    if [ -f build.gradle ] || [ -f build.gradle.kts ]; then
        BUILD_TOOL="gradle"
    elif [ -f pom.xml ]; then
        BUILD_TOOL="maven"
    else
        emit "Mutation: no JVM build file found"
        exit 1
    fi
fi

# --- detect pitest configuration ----------------------------------------
HAS_PITEST=0
case "$BUILD_TOOL" in
    gradle)
        for f in build.gradle build.gradle.kts; do
            if [ -f "$f" ] && grep -qiE '(pitest|info\.solidsoft\.pitest|pitest-gradle)' "$f"; then
                HAS_PITEST=1
                break
            fi
        done
        ;;
    maven)
        if [ -f pom.xml ] && grep -qiE '(pitest-maven|<artifactId>pitest)' pom.xml; then
            HAS_PITEST=1
        fi
        ;;
esac

if [ "$HAS_PITEST" -eq 0 ]; then
    # AC-007: capability is "not configured" — exit 0 with setup hint.
    emit "pitest not configured. Add pitest-gradle-plugin or pitest-maven-plugin to enable."
    exit 0
fi

if [ -n "${LIVESPEC_JVM_SKIP_RUN:-}" ]; then
    emit "Mutation: probe-only mode (LIVESPEC_JVM_SKIP_RUN set), pitest detected"
    exit 0
fi

# --- run pitest via the detected build tool -----------------------------
case "$BUILD_TOOL" in
    gradle)
        if [ -x ./gradlew ]; then
            GRADLE_CMD="./gradlew"
        elif command -v gradle > /dev/null 2>&1; then
            GRADLE_CMD="gradle"
        else
            emit "Mutation: neither ./gradlew nor gradle is available"
            exit 1
        fi
        if ! "$GRADLE_CMD" pitest; then
            emit "Mutation: gradle pitest task exited non-zero"
            exit 1
        fi
        # Gradle report path (AC-008).
        REPORT_PATH="build/reports/pitest/mutations.xml"
        ;;
    maven)
        if ! command -v mvn > /dev/null 2>&1; then
            emit "Mutation: mvn is not available on PATH"
            exit 1
        fi
        if ! mvn org.pitest:pitest-maven:mutationCoverage; then
            emit "Mutation: mvn pitest:mutationCoverage exited non-zero"
            exit 1
        fi
        # Maven report path (timestamped subdirectory; pick the most recent).
        # EC-004: glob the timestamped directories and pick the lexicographic max.
        REPORT_PATH=""
        for candidate in target/pit-reports/*/mutations.xml; do
            if [ -f "$candidate" ]; then
                REPORT_PATH="$candidate"
            fi
        done
        ;;
esac

if [ -z "$REPORT_PATH" ] || [ ! -f "$REPORT_PATH" ]; then
    emit "Mutation: pitest ran but mutations.xml was not produced"
    exit 1
fi

emit "Mutation: pitest report at $REPORT_PATH"
exit 0
