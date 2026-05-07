#!/usr/bin/env bash
# @spec AC-006: Properties capability detects kotest-property or jqwik.
# — .specs/features/022-driver-jvm/spec.md#ac-006
#
# kotest-property is preferred over jqwik when both are configured (Story 3 —
# Kotlin-first projects ship the kotest runner end-to-end).

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
        emit "Properties: no JVM build file found"
        exit 1
    fi
fi

# --- detect property library --------------------------------------------
HAS_PROPERTY=0
case "$BUILD_TOOL" in
    gradle)
        for f in build.gradle build.gradle.kts; do
            if [ -f "$f" ] && grep -qiE '(kotest-property|jqwik)' "$f"; then
                HAS_PROPERTY=1
                break
            fi
        done
        ;;
    maven)
        if [ -f pom.xml ] && grep -qiE '(kotest-property|jqwik)' pom.xml; then
            HAS_PROPERTY=1
        fi
        ;;
esac

if [ "$HAS_PROPERTY" -eq 0 ]; then
    emit "No property testing library found — skipping (supported: jqwik, kotest-property)"
    exit 0
fi

if [ -n "${LIVESPEC_JVM_SKIP_RUN:-}" ]; then
    emit "Properties: probe-only mode (LIVESPEC_JVM_SKIP_RUN set), library detected"
    exit 0
fi

case "$BUILD_TOOL" in
    gradle)
        if [ -x ./gradlew ]; then
            exec ./gradlew test
        elif command -v gradle > /dev/null 2>&1; then
            exec gradle test
        else
            emit "Properties: neither ./gradlew nor gradle is available"
            exit 1
        fi
        ;;
    maven)
        if ! command -v mvn > /dev/null 2>&1; then
            emit "Properties: mvn is not available on PATH"
            exit 1
        fi
        exec mvn test
        ;;
esac
