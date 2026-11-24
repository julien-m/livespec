"""The public format-23 policy inspector is read-only."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from validator.cli import app

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    ("content", "expected", "invalid"),
    [
        (None, "original", False),
        ("schema: 1\nstop_rules: amended\n", "amended", False),
        ("schema: true\nstop_rules: amended\n", "original", True),
    ],
)
def test_policy_reads_project_marker_without_writes(
    tmp_path: Path, content: str | None, expected: str, invalid: bool
) -> None:
    specs = tmp_path / ".specs"
    specs.mkdir()
    version = specs / "livespec-version"
    version.write_bytes((ROOT / "VERSION").read_bytes())
    marker = specs / "recovery-policy.yaml"
    if content is not None:
        marker.write_text(content, encoding="utf-8")
    before = {p: p.read_bytes() for p in specs.iterdir()}

    result = CliRunner().invoke(app, ["recovery", "policy", "--project", str(tmp_path), "--json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["policy"] == expected
    assert bool(payload["problem"]) == invalid
    assert {p: p.read_bytes() for p in specs.iterdir()} == before
