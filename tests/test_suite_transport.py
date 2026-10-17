"""Bind suite observations to the actual native runtime and declared npm context."""

from __future__ import annotations

import json
import os
import shlex
import shutil
from pathlib import Path

import pytest

from tests.execution_vitest_fixture import FEATURE, VitestProject
from tests.execution_vitest_fixture import vitest_dependencies as vitest_dependencies
from tests.execution_vitest_fixture import vitest_project as vitest_project
from tests.test_spec_test_observations import _prepare_local_alias
from validator.evidence_applicability import _command_key, suite_binding, suite_evidence_missing
from validator.execution_capture import capture_execution


def _capture_node(project: VitestProject, node: Path) -> Path:
    """Run bare node with a real private PATH and retain its runner-owned receipt."""
    result = capture_execution(
        ["node", str(project.root / "node_modules/vitest/vitest.mjs"), "run"],
        project_root=project.root,
        feature=FEATURE,
        adapter="junit",
        env={**os.environ, "PATH": str(node.parent) + os.pathsep + os.environ["PATH"]},
        timeout=10,
    )
    assert result.exit_code == 0 and result.receipt_path, result.stderr
    return Path(result.receipt_path)


@pytest.mark.integration
def test_suite_transport_uses_real_node_and_only_literal_npm_alias(
    vitest_project: VitestProject, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Another genuine Node22 cannot borrow the frozen runtime through proof-time PATH."""
    root = vitest_project.root
    other = root.parent / "other-native/node"
    other.parent.mkdir()
    shutil.copy2(vitest_project.node, other)
    _prepare_local_alias(root)
    vitest_project.write("test('observed', () => { expect(1).toBe(1); });")
    package = root / "package.json"
    data = json.loads(package.read_text())
    data["scripts"] = {"test": "node node_modules/vitest/vitest.mjs run"}
    package.write_text(json.dumps(data))
    plan = root / ".specs/features" / FEATURE / "plan.md"
    plan.write_text(
        "## Resolved Test Commands\n\n| Action | Command |\n|---|---|\n"
        + "| Unit | "
        + shlex.join(vitest_project.command())
        + " |\n"
    )
    monkeypatch.setenv("PATH", str(vitest_project.node.parent) + os.pathsep + os.environ["PATH"])
    binding = suite_binding(root, FEATURE, "unit")
    wrong = _capture_node(vitest_project, other)
    correct = _capture_node(vitest_project, vitest_project.node)
    evidence: dict[str, str] = {}
    actual: dict[str, list[str] | bool] = {
        "wrong_node": suite_evidence_missing(binding, wrong, root, FEATURE, evidence),
        "correct_node": suite_evidence_missing(binding, correct, root, FEATURE, evidence),
    }
    for label, argv in [("direct_alias", ["vitest", "run"]), ("npm_node", ["npm", "test"])]:
        try:
            _command_key(root, argv, root)
            actual[label] = False
        except ValueError:
            actual[label] = True
    assert actual == {
        "wrong_node": ["suite_commands_unproven"],
        "correct_node": [],
        "direct_alias": True,
        "npm_node": True,
    }
