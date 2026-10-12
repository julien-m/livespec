"""Static markdown verification for D-a subagent-header propagation.

The supervisor skills for feature and ship must prepend a synthetic
`/spec.<subcmd>` line as the FIRST line of each subagent prompt. This makes the
subagent's anti-drift directive resolve hooks under the correct sub-command
name, not under `feature`.

These tests parse the markdown statically and assert the contract.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
FEATURE_MD = REPO_ROOT / ".agent-sync" / "skills" / "spec-feature" / "SKILL.md"
SHIP_MD = REPO_ROOT / ".agent-sync" / "skills" / "spec-ship" / "SKILL.md"


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def _extract_first_line_after(marker_regex: str, text: str) -> str:
    """Return first non-empty content line of fenced block after marker regex."""
    m = re.search(marker_regex, text)
    assert m, f"marker not found: {marker_regex}"
    # Find next opening ``` after the marker
    rest = text[m.end() :]
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
        (r"Spawn a \*\*Specify agent\*\*", "/spec-specify"),
        (r"Spawn a \*\*Plan agent\*\*", "/spec-plan"),
        (r"Spawn an \*\*Implement agent\*\*", "/spec-implement"),
        (r"Spawn a \*\*Test agent\*\*", "/spec-test"),
    ],
)
def test_feature_supervisor_emits_subcommand_header(marker: str, expected: str) -> None:
    text = _read(FEATURE_MD)
    first = _extract_first_line_after(marker, text)
    assert first == expected, f"expected first line {expected!r} after {marker!r}, got {first!r}"


def test_ship_supervisor_emits_feature_header() -> None:
    text = _read(SHIP_MD)
    spawn = r"Spawn a new agent with a fresh context.*?```[a-zA-Z]*\n(.*?)```"
    m = re.search(spawn, text, re.DOTALL)
    assert m, "ship spawn block not found"
    lines = [ln.strip() for ln in m.group(1).splitlines() if ln.strip()]
    # The template opens with a "Sub-agent prompt:" label; the synthetic header follows it.
    assert lines[0].endswith("prompt:"), lines[:2]
    assert lines[1] == "/spec-feature", lines[:2]
