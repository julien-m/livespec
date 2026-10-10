"""Framework frames inside a project cannot steal a same-line assertion's origin."""

from __future__ import annotations

import ast
import json
import shutil
from pathlib import Path

import _pytest
import pluggy
import pytest

from tests.execution_evidence_support import AC, FEATURE, run
from tests.execution_evidence_support import project as project
from tests.test_execution_evidence import _rebind_assertion
from validator import execution_evidence, execution_runner
from validator.execution_evidence import verify_execution_receipt
from validator.execution_scope import digest


def _runtime_inside_project(project: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path]:
    """Use real installed pytest bytes in an explicit trusted transport fixture under the root."""
    provenance = execution_runner.runner_provenance()
    runtime = project / ".runtime"
    for module in (pytest, _pytest, pluggy):
        module_file = module.__file__
        assert module_file is not None
        shutil.copytree(Path(module_file).parent, runtime / module.__name__)
    plugin = runtime / "execution_pytest.py"
    shutil.copyfile(provenance["plugin_path"], plugin)
    provenance.update(
        pytest_path=str(runtime / "pytest/__init__.py"),
        plugin_path=str(plugin),
        plugin_sha256=digest(plugin.read_bytes()),
    )
    monkeypatch.setattr(execution_runner, "runner_provenance", lambda: provenance)
    monkeypatch.setattr(execution_evidence, "runner_provenance", lambda: provenance)
    return plugin, runtime / "pluggy/_manager.py"


def _call_line(path: Path, name: str) -> int:
    return next(
        node.lineno
        for node in ast.walk(ast.parse(path.read_text()))
        if isinstance(node, ast.Call)
        and (
            (isinstance(node.func, ast.Name) and node.func.id == name)
            or (isinstance(node.func, ast.Attribute) and node.func.attr == name)
        )
    )


@pytest.mark.parametrize("collision", ["plugin", "pluggy"])
def test_same_line_framework_callback_does_not_change_real_assertion_origin(
    project: Path, monkeypatch: pytest.MonkeyPatch, collision: str
) -> None:
    plugin, manager = _runtime_inside_project(project, monkeypatch)
    line = (
        _call_line(plugin, "_assertion_origin")
        if collision == "plugin"
        else _call_line(manager, "_inner_hookexec")
    )
    source = "from app import add\n\ndef test_add():\n" + "\n" * (line - 4)
    _rebind_assertion(project, source + "    assert add(1, 2) == 3\n", line)
    receipt = run(project)
    trace = json.loads((receipt.parent / "assertions").read_text())["assertions"]
    assert len(trace) == 1
    assert trace[0]["line"] == line and trace[0]["path"] == str(project / "test_app.py")
    result = verify_execution_receipt(receipt, project, FEATURE, (AC,))
    assert result.valid and result.certified_acs == [AC], result.gaps


def test_helper_assertion_inside_root_cannot_impersonate_an_unexecuted_test_assertion(
    project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _runtime_inside_project(project, monkeypatch)
    _rebind_assertion(
        project,
        "from app import add\nfrom helper import check\ndef test_add():\n"
        "    if False:\n        assert add(1, 2) == 3\n    check()\n",
        5,
    )
    (project / "helper.py").write_text(
        "from app import add\n\ndef check():\n\n    assert add(1, 2) == 3\n"
    )
    (project / "conftest.py").write_text(
        'import pytest\npytest.register_assert_rewrite("helper")\n'
    )
    receipt = run(project)
    trace = json.loads((receipt.parent / "assertions").read_text())["assertions"]
    assert trace[0]["path"] == str(project / "helper.py")
    result = verify_execution_receipt(receipt, project, FEATURE, (AC,))
    assert not result.valid and not result.certified_acs
