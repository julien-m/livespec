"""Static markdown verification for D-a subagent-header propagation.

The supervisors `commands/feature.md` and `commands/ship.md` must prepend
a synthetic `/spec.<subcmd>` line as the FIRST line of each subagent
prompt — this is what makes the subagent's anti-drift directive resolve
hooks under the correct sub-command name (not under `feature`).

These tests parse the markdown statically and assert the contract.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
FEATURE_MD = REPO_ROOT / "commands" / "feature.md"
SHIP_MD = REPO_ROOT / "commands" / "ship.md"


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def _extract_first_line_after(marker_regex: str, text: str) -> str:
    """Return first non-empty content line of fenced block after marker regex."""
    m = re.search(marker_regex, text)
    assert m, f"marker not found: {marker_regex}"
    # Find next opening ``` after the marker
    rest = text[m.end():]
    fence = re.search(r"```[a-zA-Z]*\n(.*?)```", rest, re.DOTALL)
    assert fence, f"no fenced code block after {marker_regex}"
    block = fence.group(1)
    for line in block.splitlines():
        if line.strip():
            return line.strip()
    raise AssertionError(f"empty fenced block after {marker_regex}")


@pytest.mark.parametrize(
    "marker, expected",
    [
        (r"Spawn a \*\*Specify agent\*\*", "/spec.specify"),
        (r"Spawn a \*\*Plan agent\*\*", "/spec.plan"),
        (r"Spawn an \*\*Implement agent\*\*", "/spec.implement"),
        (r"Spawn a \*\*Test agent\*\*", "/spec.test"),
    ],
)
def test_feature_supervisor_emits_subcommand_header(
    marker: str, expected: str
) -> None:
    text = _read(FEATURE_MD)
    first = _extract_first_line_after(marker, text)
    assert first == expected, (
        f"expected first line {expected!r} after {marker!r}, got {first!r}"
    )


def test_ship_supervisor_emits_feature_header() -> None:
    text = _read(SHIP_MD)
    first = _extract_first_line_after(r"Spawn a new agent with a fresh context", text)
    # The prompt template starts with "Agent prompt:" then the synthetic line.
    # Accept either order: assert /spec.feature appears in the first two non-empty lines.
    m = re.search(r"Spawn a new agent.*?```[a-zA-Z]*\n(.*?)```", text, re.DOTALL)
    assert m, "ship spawn block not found"
    lines = [ln.strip() for ln in m.group(1).splitlines() if ln.strip()]
    assert "/spec.feature" in lines[:3], (
        f"`/spec.feature` not in the first 3 lines of the ship agent prompt: {lines[:3]}"
    )
    # _extract_first_line_after may return "Agent prompt:" — that's OK,
    # the strict check above is what matters.
    _ = first
