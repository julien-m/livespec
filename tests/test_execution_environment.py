"""Tests may mutate their environment without changing the runner's capture identity."""

import json
from pathlib import Path

import pytest

from tests.execution_evidence_support import AC, FEATURE, run
from tests.execution_evidence_support import project as project
from tests.test_execution_evidence import _rebind_assertion
from validator.execution_evidence import verify_execution_receipt


def test_assertion_survives_temporarily_cleared_environment(project: Path) -> None:
    source = (
        "import os\nfrom app import add\ndef test_add():\n"
        "    saved = dict(os.environ)\n    try:\n        os.environ.clear()\n"
        "        assert add(1, 2) == 3\n    finally:\n        os.environ.update(saved)\n"
    )
    _rebind_assertion(project, source, 7)
    receipt = run(project)
    result = verify_execution_receipt(receipt, project, FEATURE, (AC,))
    assert result.valid and result.certified_acs == [AC], result.gaps
    assert result.executed_tests[0].assertion_count == 1


@pytest.mark.parametrize("mutation", ["clear", "replace"])
def test_session_finish_uses_original_runner_identity_and_trace_path(
    project: Path, mutation: str
) -> None:
    action = (
        "os.environ.clear()"
        if mutation == "clear"
        else (
            "os.environ.update(LIVESPEC_EXECUTION_PROJECT='foreign-root', "
            "LIVESPEC_EXECUTION_NONCE='foreign-nonce', "
            "LIVESPEC_EXECUTION_FEATURE='foreign-feature', "
            "LIVESPEC_ASSERTION_TRACE='redirected-trace.json')"
        )
    )
    (project / "conftest.py").write_text(
        "import os, pytest\n@pytest.hookimpl(tryfirst=True)\ndef pytest_sessionfinish():\n"
        f"    {action}\n"
    )
    receipt = run(project)
    result = verify_execution_receipt(receipt, project, FEATURE, (AC,))
    assert result.valid and result.certified_acs == [AC], result.gaps
    trace = json.loads((receipt.parent / "assertions").read_text())
    assert trace["project_root"] == str(project)
    assert trace["feature"] == FEATURE and trace["invocation"] == receipt.parent.name
    assert len(trace["assertions"]) == 1
    assert not (project / "redirected-trace.json").exists()
