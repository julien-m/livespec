# LiveSpec traceability anchors
# @spec(FR-028)

"""Compiler registry for native User Journey runner backends."""

# @spec FR-028: native runner compiler registry
# — .specs/features/057-cross-feature-user-journeys-v2/spec.md#fr-028

from __future__ import annotations

from dataclasses import dataclass

from .schema import JourneyRunner


@dataclass(frozen=True)
class CompilerBackend:
    """Registered native compiler backend metadata."""

    runner: str
    artifact_kind: str


_BACKENDS = {
    JourneyRunner.PLAYWRIGHT.value: CompilerBackend(
        runner=JourneyRunner.PLAYWRIGHT.value,
        artifact_kind="playwright",
    ),
    JourneyRunner.XCUITEST.value: CompilerBackend(
        runner=JourneyRunner.XCUITEST.value,
        artifact_kind="xcuitest",
    ),
    JourneyRunner.MAESTRO.value: CompilerBackend(
        runner=JourneyRunner.MAESTRO.value,
        artifact_kind="maestro",
    ),
}


def get_compiler_backend(runner: str) -> CompilerBackend | None:
    """Return the native compiler backend for a runner when supported."""
    return _BACKENDS.get(runner)


def supported_native_runners() -> set[str]:
    """Return runner names with native compiler backends."""
    return set(_BACKENDS)


__all__ = ["CompilerBackend", "get_compiler_backend", "supported_native_runners"]
