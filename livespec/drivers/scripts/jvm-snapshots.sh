#!/usr/bin/env bash
# @spec AC-005: Snapshot capability detects kotest-snapshot or approvaltests-java.
# — .specs/features/022-driver-jvm/spec.md#ac-005
#
# Detects build tool and snapshot library; runs the build tool's standard test
# task. If neither library is configured, emits the skip-message and exits 0
# (matches the spec contract — the capability is "not configured", not broken).
#
# Environment overrides:
#   LIVESPEC_JVM_BUILD_TOOL  — force "gradle" or "maven"
#   LIVESPEC_JVM_SKIP_RUN=1  — probe only (do not invoke gradle/mvn)

set -u
set -o pipefail

emit() {
    printf '%s\n' "$*"
}

# --- detect build tool (Gradle priority, AC-010) ------------------------
BUILD_TOOL="${LIVESPEC_JVM_BUILD_TOOL:-}"
if [ -z "$BUILD_TOOL" ]; then
    if [ -f build.gradle ] || [ -f build.gradle.kts ]; then
        BUILD_TOOL="gradle"
    elif [ -f pom.xml ]; then
        BUILD_TOOL="maven"
    else
        emit "Snapshots: no JVM build file found"
        exit 1
    fi
fi

# --- detect snapshot library --------------------------------------------
HAS_SNAPSHOT=0
case "$BUILD_TOOL" in
    gradle)
        for f in build.gradle build.gradle.kts; do
            if [ -f "$f" ] && grep -qiE '(kotest-snapshot|approvaltests)' "$f"; then
                HAS_SNAPSHOT=1
                break
            fi
        done
        ;;
    maven)
        if [ -f pom.xml ] && grep -qiE '(kotest-snapshot|approvaltests)' pom.xml; then
            HAS_SNAPSHOT=1
        fi
        ;;
esac

if [ "$HAS_SNAPSHOT" -eq 0 ]; then
    emit "No snapshot library detected — skipping (supported: kotest-snapshot, approvaltests)"
    exit 0
fi

# --- run tests via the detected build tool ------------------------------
if [ -n "${LIVESPEC_JVM_SKIP_RUN:-}" ]; then
    emit "Snapshots: probe-only mode (LIVESPEC_JVM_SKIP_RUN set), library detected"
    exit 0
fi

case "$BUILD_TOOL" in
    gradle)
        if [ -x ./gradlew ]; then
            exec ./gradlew test
        elif command -v gradle > /dev/null 2>&1; then
            exec gradle test
        else
            emit "Snapshots: neither ./gradlew nor gradle is available"
            exit 1
        fi
        ;;
    maven)
        if ! command -v mvn > /dev/null 2>&1; then
            emit "Snapshots: mvn is not available on PATH"
            exit 1
        fi
        exec mvn test
        ;;
esac
