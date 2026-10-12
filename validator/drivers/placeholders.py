# LiveSpec traceability anchors
# @spec(FR-002)
# @spec(AC-002)
# @spec(AC-004)
# @spec(AC-012)
# @spec(FR-004)

"""Resolve driver command placeholders before a capability subprocess starts."""

# @spec FR-002: Module auto-detection feeds {module}
# — .specs/features/017-driver-python/spec.md#fr-002
# @spec AC-002: Coverage runs with concrete module/report/threshold values
# — .specs/features/017-driver-python/spec.md#ac-002
# @spec AC-004: Module defaults to the inferred package; overrides replace the command
# — .specs/features/017-driver-python/spec.md#ac-004
# @spec FR-002, FR-004, AC-002, AC-012: {js_*} tokens follow the detected runner and
# package manager — .specs/features/018-driver-typescript-javascript/spec.md#fr-002

from __future__ import annotations

import re
from pathlib import Path

from .python_detector import detect_python_module
from .schemas import DriverCapability
from .typescript_detector import (
    detect_package_manager,
    detect_test_runner,
    package_manager_exec,
    runner_argv,
)

_PLACEHOLDER_RE = re.compile(r"\{(module|report_path|threshold)\}")


def _js_tokens(name: str, project_root: Path) -> list[str]:
    """Expand a whole-token JavaScript placeholder into argv entries."""
    root = str(project_root)
    if name == "{js_exec}":
        return package_manager_exec(detect_package_manager(root))
    return runner_argv(detect_test_runner(root), coverage=name == "{js_coverage_args}")


_SPLAT_TOKENS = frozenset({"{js_exec}", "{js_coverage_args}", "{js_test_args}"})


def _format_threshold(threshold: float) -> str:
    """Render integral thresholds without a trailing ``.0`` for CLI flags."""
    return str(int(threshold)) if float(threshold).is_integer() else str(threshold)


def _placeholder_value(
    name: str, cap: DriverCapability, project_root: Path, driver_name: str
) -> str:
    """Return the concrete value of one supported placeholder.

    Raises:
        ValueError: The capability lacks the field the placeholder refers to.
    """
    if name == "module":
        return detect_python_module(str(project_root))
    if name == "report_path":
        if cap.report_path is None:
            raise ValueError(f"Driver {driver_name!r} uses {{report_path}} without report_path")
        return cap.report_path
    if cap.threshold is None:
        raise ValueError(f"Driver {driver_name!r} uses {{threshold}} without threshold")
    return _format_threshold(cap.threshold)


def resolve_argv_placeholders(
    argv: list[str], cap: DriverCapability, project_root: Path, driver_name: str
) -> list[str]:
    """Substitute driver placeholders in each argv token.

    ``{module}``, ``{report_path}`` and ``{threshold}`` are replaced inside a
    token after ``shlex`` splitting, so values never change token boundaries.
    Whole tokens ``{js_exec}``, ``{js_coverage_args}`` and ``{js_test_args}``
    expand to several entries from the detected package manager (FR-004) and
    test runner (FR-002). Other brace text is preserved verbatim.

    Args:
        argv: Command tokens split from the manifest ``command``.
        cap: Capability block supplying ``report_path`` and ``threshold``.
        project_root: Project whose Python module is detected for ``{module}``.
        driver_name: Driver name used in error messages.

    Returns:
        Tokens with every supported placeholder replaced.

    Raises:
        ValueError: A placeholder references a field the capability does not declare.
    """
    resolved: list[str] = []
    for token in argv:
        if token in _SPLAT_TOKENS:
            resolved.extend(_js_tokens(token, project_root))
            continue
        resolved.append(
            _PLACEHOLDER_RE.sub(
                lambda match: _placeholder_value(match.group(1), cap, project_root, driver_name),
                token,
            )
        )
    return resolved


__all__ = ["resolve_argv_placeholders"]
