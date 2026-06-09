# LiveSpec traceability anchors
# @spec(FR-033)
# @spec(FR-034)
# @spec(FR-035)

"""Native deterministic visual checks for User Journeys v2."""

# @spec FR-034, FR-035: native visual checks and visual modes
# — .specs/features/057-cross-feature-user-journeys-v2/spec.md#fr-034

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ElementBounds:
    """Measured rectangle for one UI element."""

    x: int
    y: int
    width: int
    height: int


@dataclass(frozen=True)
class NativeVisualCheckResult:
    """Result of a deterministic native visual check."""

    passed: bool
    reason: str
    measurements: dict[str, int] = field(default_factory=dict)


def evaluate_native_visual_check(
    *,
    assertion: str,
    element: ElementBounds,
    parent: ElementBounds,
    min_px: int | None = None,
) -> NativeVisualCheckResult:
    """Evaluate a deterministic visual check from measured bounds."""
    if assertion == "min_margin":
        return _evaluate_min_margin(element, parent, min_px or 0)
    if assertion == "text_fits":
        return _evaluate_text_fits(element, parent)
    return NativeVisualCheckResult(
        passed=False,
        reason="native_visual_assertion_unsupported",
    )


def _evaluate_min_margin(
    element: ElementBounds,
    parent: ElementBounds,
    min_px: int,
) -> NativeVisualCheckResult:
    """Evaluate whether every side has at least the required margin."""
    measurements = {
        "left_margin": element.x - parent.x,
        "right_margin": parent.x + parent.width - (element.x + element.width),
        "top_margin": element.y - parent.y,
        "bottom_margin": parent.y + parent.height - (element.y + element.height),
    }
    passed = all(value >= min_px for value in measurements.values())
    return NativeVisualCheckResult(
        passed=passed,
        reason="ok" if passed else "margin_below_minimum",
        measurements=measurements,
    )


def _evaluate_text_fits(
    element: ElementBounds,
    parent: ElementBounds,
) -> NativeVisualCheckResult:
    """Evaluate whether measured text bounds fit inside its parent."""
    overflows = (
        element.x < parent.x
        or element.y < parent.y
        or element.x + element.width > parent.x + parent.width
        or element.y + element.height > parent.y + parent.height
    )
    return NativeVisualCheckResult(
        passed=not overflows,
        reason="text_overflows_parent" if overflows else "ok",
        measurements={"element_width": element.width, "parent_width": parent.width},
    )


__all__ = [
    "ElementBounds",
    "NativeVisualCheckResult",
    "evaluate_native_visual_check",
]
