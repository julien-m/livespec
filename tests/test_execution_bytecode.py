"""Actual pytest bytecode warmed without assertion hooks cannot erase capture evidence."""

from __future__ import annotations

import marshal
import os
import subprocess
import sys
from pathlib import Path
from types import CodeType

import pytest

from tests.execution_evidence_support import AC, FEATURE, run
from tests.execution_evidence_support import project as project
from validator.execution_evidence import verify_execution_receipt


def _code_names(code: CodeType) -> set[str]:
    names = set(code.co_names)
    for value in code.co_consts:
        if isinstance(value, CodeType):
            names.update(_code_names(value))
    return names


@pytest.mark.parametrize("caller_prefix", [False, True])
def test_actual_warm_pytest_cache_cannot_suppress_runner_assertions(
    project: Path, monkeypatch: pytest.MonkeyPatch, caller_prefix: bool
) -> None:
    prefix = project.parent / "preexisting-bytecode"
    if caller_prefix:
        monkeypatch.setenv("PYTHONPYCACHEPREFIX", str(prefix))
    else:
        monkeypatch.delenv("PYTHONPYCACHEPREFIX", raising=False)
    warmed = subprocess.run(
        [sys.executable, "-m", "pytest", "test_app.py", "-q"],
        cwd=project,
        env=dict(os.environ),
        capture_output=True,
        text=True,
        check=False,
    )
    assert warmed.returncode == 0, warmed.stderr
    directory = prefix if caller_prefix else project / "__pycache__"
    path = next(directory.rglob("test_app.*-pytest-*.pyc"))
    original = path.read_bytes()
    names = _code_names(marshal.loads(original[16:]))
    assert not any("assertion_pass" in name for name in names)
    receipt = run(project)
    result = verify_execution_receipt(receipt, project, FEATURE, (AC,))
    assert result.valid and result.certified_acs == [AC], result.gaps
    assert sum(test.assertion_count or 0 for test in result.executed_tests) == 1
    assert path.read_bytes() == original
    isolated = list((receipt.parent / "bytecode").rglob("test_app.*-pytest-*.pyc"))
    assert len(isolated) == 1
    assert any(
        "assertion_pass" in name
        for name in _code_names(marshal.loads(isolated[0].read_bytes()[16:]))
    )
