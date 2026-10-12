# LiveSpec traceability anchors
# @spec(AC-002)
# @spec(AC-004)

"""`livespec test` resolves the Python driver placeholders before running pytest."""

# @spec AC-002: Coverage runs concrete module/report/threshold values
# — .specs/features/017-driver-python/spec.md#ac-002
# @spec AC-004: Module inferred from pyproject.toml
# — .specs/features/017-driver-python/spec.md#ac-004

from __future__ import annotations

import json
import stat
from pathlib import Path

import pytest
from pytest import MonkeyPatch
from typer.testing import CliRunner

from validator.cli import app

_FAKE_PYTEST = """#!/usr/bin/env python3
import json, pathlib, sys
pathlib.Path(sys.argv[0]).with_name("argv.json").write_text(json.dumps(sys.argv[1:]))
for arg in sys.argv[1:]:
    if arg.startswith("--cov-report=lcov:"):
        pathlib.Path(arg.split(":", 1)[1]).write_text("SF:a.py\\nDA:1,1\\nend_of_record\\n")
"""


@pytest.mark.level_3a
def test_livespec_test_passes_detected_module_to_python_coverage(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    """The real `livespec test` flow substitutes `{module}` via the Python detector."""
    project = tmp_path / "project"
    (project / ".specs").mkdir(parents=True)
    (project / "pyproject.toml").write_text('[project]\nname = "Acme-Shop"\n', encoding="utf-8")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake = bin_dir / "pytest"
    fake.write_text(_FAKE_PYTEST, encoding="utf-8")
    fake.chmod(fake.stat().st_mode | stat.S_IXUSR)
    monkeypatch.setenv("PATH", f"{bin_dir}:/usr/bin:/bin")
    monkeypatch.chdir(project)

    result = CliRunner().invoke(app, ["test"])

    assert result.exit_code == 0, result.output
    argv = json.loads((bin_dir / "argv.json").read_text(encoding="utf-8"))
    assert argv == [
        "--cov=acme_shop",
        "--cov-report=lcov:lcov.info",
        "--cov-fail-under=80",
    ]
    assert "Coverage: 100.0%" in result.output
