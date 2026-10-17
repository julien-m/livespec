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


@pytest.mark.parametrize("wrapper", ["nested-array", "promise"])
@pytest.mark.parametrize("hook", ["config", "configResolved", "apply"])
def test_wrapped_configuration_lifecycle_plugins_fail_closed(
    vitest_project: VitestProject, wrapper: str, hook: str
) -> None:
    """Reject every wrapped config mutation before it can replace the owned runtime."""
    root = vitest_project.root
    plugin = (
        "{name:'mutates-owned-runtime', " + hook + "(config) { "
        "writeFileSync('lifecycle-ran', 'yes'); "
        "config.test.runner = './missing-user-runner.ts'; config.test.reporters = []; }}"
    )
    option = "[false, [null, undefined, " + plugin + "]]"
    if wrapper == "promise":
        option = "Promise.resolve(" + plugin + ")"
    (root / "vitest.config.ts").write_text(
        "import {writeFileSync} from 'node:fs'; export default {plugins:["
        + option
        + "],test:{maxWorkers:1,minWorkers:1}};"
    )
    vitest_project.write("test('unreached body', () => { expect(1).toBe(1); });")
    receipt = vitest_project.capture()
    assert not (root / "lifecycle-ran").exists(), "A wrapped lifecycle plugin executed"
    diagnostic = (receipt.parent / "stderr").read_text()
    assert "Unsupported configuration" in diagnostic, diagnostic
    result = verify_execution_observation(receipt, root, FEATURE, "passed")
    assert not result.valid


@pytest.mark.parametrize("option", ["{plugin:{name:'hidden'}}", "42"])
def test_unknown_configuration_plugin_options_fail_closed(
    vitest_project: VitestProject, option: str
) -> None:
    """Refuse unrecognized options explicitly rather than accepting Vite's later handling."""
    root = vitest_project.root
    (root / "vitest.config.ts").write_text("export default {plugins:[" + option + "]};")
    vitest_project.write("test('unknown wrapper', () => { expect(1).toBe(1); });")
    receipt = vitest_project.capture()
    diagnostic = (receipt.parent / "stderr").read_text()
    assert "Unsupported configuration" in diagnostic, diagnostic
    assert not verify_execution_observation(receipt, root, FEATURE, "passed").valid


@pytest.mark.parametrize("phase", ["serve", "build"])
def test_nested_ordinary_configuration_plugin_remains_supported(
    vitest_project: VitestProject,
    phase: str,
) -> None:
    """Flatten arrays/falsy options while retaining a real ordinary transform plugin."""
    root = vitest_project.root
    (root / ".specs/.execution").mkdir(exist_ok=True)
    (root / "vitest.config.ts").write_text(
        "import {writeFileSync} from 'node:fs'; "
        "export default {plugins:[false,[null,undefined,{name:'ordinary', "
        f"apply:'{phase}', "
        "transform(source,id) { if(id.endsWith('matchers.test.ts')) "
        "writeFileSync('.specs/.execution/transform-ran','yes'); return null; }}]], "
        "test:{maxWorkers:1,minWorkers:1}};"
    )
    vitest_project.write(
        "test('ordinary plugin', async () => { "
        "await expect(Promise.resolve(1)).resolves.toBe(1); });"
    )
    receipt = vitest_project.capture()
    result = verify_execution_observation(receipt, root, FEATURE, "passed")
    assert result.valid, result.gaps
    assert (root / ".specs/.execution/transform-ran").exists() is (phase == "serve")
