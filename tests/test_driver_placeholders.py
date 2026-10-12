# LiveSpec traceability anchors
# @spec(FR-002)

"""Unit tests for driver command placeholder resolution."""

# @spec FR-002: {module} comes from the Python module detector
# — .specs/features/017-driver-python/spec.md#fr-002

from __future__ import annotations

from pathlib import Path

import pytest

from validator.drivers.placeholders import resolve_argv_placeholders
from validator.drivers.schemas import DriverCapability


def test_resolves_each_token_without_changing_token_boundaries(tmp_path: Path) -> None:
    """Values with spaces stay in their original argv token; unknown braces survive."""
    (tmp_path / "src").mkdir()
    cap = DriverCapability(command="x", report_path="out dir/lcov.info", threshold=72.5)

    argv = resolve_argv_placeholders(
        ["pytest", "--cov={module}", "--cov-report=lcov:{report_path}", "-k", "{other}"],
        cap,
        tmp_path,
        "python",
    )

    assert argv == ["pytest", "--cov=src", "--cov-report=lcov:out dir/lcov.info", "-k", "{other}"]
    assert resolve_argv_placeholders(["{threshold}"], cap, tmp_path, "python") == ["72.5"]


@pytest.mark.parametrize("token", ["{report_path}", "{threshold}"])
def test_missing_capability_field_is_a_manifest_error(tmp_path: Path, token: str) -> None:
    """A placeholder without its backing field fails before any subprocess starts."""
    cap = DriverCapability(command="x")

    with pytest.raises(ValueError, match=token.strip("{}")):
        resolve_argv_placeholders([token], cap, tmp_path, "custom")
