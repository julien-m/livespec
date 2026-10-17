"""Consumer directory names never confer ownership of LiveSpec observer assets."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from tests.execution_vitest_fixture import FEATURE, VitestProject
from tests.execution_vitest_fixture import vitest_dependencies as vitest_dependencies
from tests.execution_vitest_fixture import vitest_project as vitest_project
from validator.execution_evidence import verify_execution_observation

pytestmark = pytest.mark.integration


@pytest.mark.parametrize("location", ["project-root", "test-subdirectory", "directory-lookalike"])
def test_consumer_asset_names_remain_instrumented_and_bound(
    vitest_project: VitestProject, tmp_path: Path, location: str
) -> None:
    """Observe real sync/await matchers and bind imported sources despite observer-like names."""
    project = vitest_project
    if location == "project-root":
        root = tmp_path / "validator/vitest/consumer"
        root.parent.mkdir(parents=True)
        project.root.rename(root)
        project = VitestProject(root, project.node)
    directory = project.root
    if location != "project-root":
        directory /= (
            "validator/vitest" if location == "test-subdirectory" else "validator/vitest-neighbor"
        )
        directory.mkdir(parents=True)
    helper = directory / "value.ts"
    helper.write_text("export const value = 1;\n")
    source = project.write(
        "import {value} from './value'; "
        "test('owned consumer source', async () => { "
        "expect(value).toBe(1); await expect(Promise.resolve(value)).resolves.toBe(1); });",
        str((directory / "ownership.test.ts").relative_to(project.root)),
    )
    receipt = project.capture()
    result = verify_execution_observation(receipt, project.root, FEATURE, "passed")
    assert result.valid, result.gaps
    inventory = json.loads((receipt.parent / "inventory").read_text())
    for path in (source, helper):
        local = path.relative_to(project.root).as_posix()
        assert inventory["bound_inputs"][local] == hashlib.sha256(path.read_bytes()).hexdigest()
    assertions = json.loads((receipt.parent / "assertions").read_text())["assertions"]
    assert len(assertions) == 2
    assert {item["path"] for item in assertions} == {source.relative_to(project.root).as_posix()}
    assert all(
        not Path(path).is_absolute() and not path.startswith("../")
        for path in inventory["bound_inputs"]
    )
