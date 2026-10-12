"""`livespec bugfix capture` observes RED/GREEN via runner-owned receipts (084 AC-001/002)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from tests.bugfix_support import FEATURE, FIXED, TEST, BugfixProject, make_project


@pytest.fixture
def project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> BugfixProject:
    built = make_project(tmp_path)
    built.write("tests/test_calc.py", TEST)
    monkeypatch.chdir(built.root)
    return built


def test_failing_assertion_is_red_and_receipt_is_runner_owned(project: BugfixProject) -> None:
    code, receipt = project.capture("red")

    assert code == 0
    assert Path(receipt).parent.parent == project.root.resolve() / ".specs" / ".execution"
    assert Path(receipt).is_file()


def test_failure_without_assertion_is_not_red(project: BugfixProject) -> None:
    project.write("tests/test_calc.py", "def test_add():\n    raise TypeError('boom')\n")

    code, receipt = project.capture("red")

    assert code == 1
    assert Path(receipt).is_file()


def test_passing_run_is_green_but_not_red(project: BugfixProject) -> None:
    project.write("calc.py", FIXED)

    assert project.capture("green")[0] == 0
    assert project.capture("red")[0] == 1


def test_failing_run_is_not_green(project: BugfixProject) -> None:
    assert project.capture("green")[0] == 1


def test_json_output_and_usage_errors(project: BugfixProject) -> None:
    command = f"{sys.executable} -m pytest -q -p no:cacheprovider tests/test_calc.py"
    result = project.run(
        "bugfix", "capture", "--feature", FEATURE, "--expect", "red", "--command", command, "--json"
    )
    payload = json.loads(result.output)
    assert result.exit_code == 0
    assert set(payload) == {"receipt_path", "expected", "observed", "exit_code", "gaps"}
    assert payload["observed"] is True and payload["exit_code"] == 1

    executions = project.root / ".specs" / ".execution"
    before = sorted(executions.iterdir())
    bad_expect = project.run(
        "bugfix", "capture", "--feature", FEATURE, "--expect", "blue", "--command", command
    )
    unknown = project.run(
        "bugfix", "capture", "--feature", "999-none", "--expect", "red", "--command", command
    )
    assert bad_expect.exit_code == 2 and unknown.exit_code == 2
    assert sorted(executions.iterdir()) == before  # nothing ran
