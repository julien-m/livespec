"""Evidence input parsing for `livespec goal prove --evidence`."""

from __future__ import annotations

import json
from pathlib import Path

from validator.goal_cli_inputs import read_evidence_input


def test_long_inline_evidence_json_is_parsed_not_stat_as_a_path() -> None:
    """Inline JSON longer than NAME_MAX must not raise ENAMETOOLONG on Python < 3.14."""
    evidence = {"qe_boundary_note": "x" * 400}
    assert read_evidence_input(json.dumps(evidence)) == evidence


def test_evidence_file_path_is_read(tmp_path: Path) -> None:
    """An existing file path still wins over inline parsing."""
    path = tmp_path / "evidence.json"
    path.write_text(json.dumps({"output": "done"}), encoding="utf-8")
    assert read_evidence_input(str(path)) == {"output": "done"}
