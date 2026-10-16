"""Genuine Vitest refusal proofs for substituted runtimes and mismatched evidence origins."""

from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path

import pytest

from tests.execution_vitest_fixture import FEATURE, VitestProject
from tests.execution_vitest_fixture import vitest_dependencies as vitest_dependencies
from tests.execution_vitest_fixture import vitest_project as vitest_project
from validator import execution_vitest, execution_vitest_provenance
from validator.execution_capture import CaptureResult, capture_execution
from validator.execution_evidence import verify_execution_observation
from validator.execution_scope import digest

pytestmark = pytest.mark.integration
PASSING = "test('real matcher', () => { expect(1).toBe(1); });"


def _capture_argv(project: VitestProject, argv: list[str]) -> CaptureResult:
    """Execute arbitrary fixture argv through the actual bounded capture authority."""
    return capture_execution(
        argv,
        project_root=project.root,
        feature=FEATURE,
        adapter="junit",
        env=dict(os.environ),
        timeout=10,
    )


def _rebind_trace(project: VitestProject, receipt: Path, payload: bytes) -> None:
    """Rebind intentionally corrupt trace hashes so semantic origin checks are exercised."""
    project.replace_artifact(receipt, "assertions", payload)
    capture_path = receipt.parent / "capture.json"
    capture = json.loads(capture_path.read_text())
    capture["assertion_trace_sha256"] = digest(payload)
    project.replace_artifact(receipt, "capture.json", json.dumps(capture).encode())
    reference = json.loads(receipt.read_text())
    reference["capture_sha256"] = digest(capture_path.read_bytes())
    project.replace_artifact(receipt, receipt.name, json.dumps(reference).encode())


@pytest.mark.parametrize("kind", ["native-python", "script-wrapper"])
def test_substituted_native_runtime_and_script_wrapper_are_rejected(
    vitest_project: VitestProject, kind: str
) -> None:
    """Reject a genuine non-Node native executable and an executable shell wrapper."""
    vitest_project.write(PASSING)
    executable = Path(sys.executable).resolve()
    marker = vitest_project.root / "wrapper-ran"
    if kind == "script-wrapper":
        executable = vitest_project.root / "node-wrapper"
        executable.write_text("#!/bin/sh\ntouch wrapper-ran\nexit 0\n")
        executable.chmod(0o700)
    argv = vitest_project.command()
    argv[0] = str(executable)
    with pytest.raises(ValueError) as rejected:
        _capture_argv(vitest_project, argv)
    print(json.dumps({"case": kind, "diagnostic": str(rejected.value)}))
    assert "Node" in str(rejected.value)
    assert not marker.exists()


def test_initial_shadow_entry_outside_the_local_package_is_rejected(
    vitest_project: VitestProject,
) -> None:
    """Reject a similarly named entry before it can run outside the governed local package."""
    vitest_project.write(PASSING)
    shadow = vitest_project.root / "vitest.mjs"
    shadow.write_text("throw Error('shadow entry must never run');")
    argv = vitest_project.command()
    argv[1] = str(shadow)
    with pytest.raises(ValueError) as rejected:
        _capture_argv(vitest_project, argv)
    print(json.dumps({"case": "shadow-entry", "diagnostic": str(rejected.value)}))
    assert "selected package's local vitest/vitest.mjs" in str(rejected.value)


def test_installed_vitest_package_cannot_escape_through_a_symlink(
    vitest_project: VitestProject,
) -> None:
    """Reject genuine installed package bytes reached through an escaping module symlink."""
    root = vitest_project.root
    vitest_project.write(PASSING)
    package = root / "node_modules/vitest"
    escaped = root.parent / "escaped-vitest"
    package.rename(escaped)
    package.symlink_to(escaped, target_is_directory=True)
    with pytest.raises(ValueError) as rejected:
        vitest_project.capture()
    print(json.dumps({"case": "module-escape", "diagnostic": str(rejected.value)}))
    assert "symlink escapes" in str(rejected.value)


def test_substituted_installed_runner_metadata_is_rejected(vitest_project: VitestProject) -> None:
    """Reject replacement runner metadata before selected test execution."""
    vitest_project.write(PASSING)
    manifest = vitest_project.root / "node_modules/@vitest/runner/package.json"
    metadata = json.loads(manifest.read_text())
    metadata["version"] = "3.0.0"
    manifest.write_text(json.dumps(metadata))
    with pytest.raises(ValueError) as rejected:
        vitest_project.capture()
    print(json.dumps({"case": "module-substitution", "diagnostic": str(rejected.value)}))
    assert "Unsupported local @vitest/runner" in str(rejected.value)


@pytest.mark.parametrize(
    "source",
    ["test('counter only', () => { expect.assertions(0); });", "test.todo('todo');"],
    ids=["counter-only", "todo-only"],
)
def test_assertion_counters_and_todo_only_cannot_qualify(
    vitest_project: VitestProject, source: str
) -> None:
    """Refuse nominally green selections containing counters or todo declarations alone."""
    vitest_project.write(source)
    receipt = vitest_project.capture()
    capture = json.loads((receipt.parent / "capture.json").read_text())
    assert capture["exit_code"] == 0
    result = verify_execution_observation(receipt, vitest_project.root, FEATURE, "passed")
    print(json.dumps({"case": source, "gaps": result.gaps}))
    assert not result.valid
    assert result.gaps


def test_report_only_replacement_with_real_package_metadata_cannot_qualify(
    vitest_project: VitestProject,
) -> None:
    """Refuse a successful replacement entry that writes XML but no runner-owned matcher trace."""
    root = vitest_project.root
    vitest_project.write(PASSING)
    metadata = json.loads((root / "node_modules/vitest/package.json").read_text())
    assert metadata["version"] == "2.1.9"
    (root / "node_modules/vitest/vitest.mjs").write_text(
        "import {writeFileSync} from 'node:fs';\n"
        "writeFileSync(process.env.LIVESPEC_VITEST_JUNIT, "
        '\'<testsuites><testsuite><testcase classname="fake" name="fake"/>\''
        "+'</testsuite></testsuites>'); console.log('report-only replacement ran');"
    )
    receipt = vitest_project.capture()
    capture = json.loads((receipt.parent / "capture.json").read_text())
    assert capture["exit_code"] == 0
    assert "report-only replacement ran" in (receipt.parent / "stdout").read_text()
    assert capture["assertion_trace_sha256"] is None
    result = verify_execution_observation(receipt, root, FEATURE, "passed")
    print(json.dumps({"case": "report-only replacement", "gaps": result.gaps}))
    assert not result.valid


def test_lock_mutation_during_a_real_matcher_run_invalidates_the_observation(
    vitest_project: VitestProject,
) -> None:
    """Reject changed governed inputs even though the real test and matcher pass."""
    vitest_project.write(
        "import {appendFileSync} from 'node:fs';\n"
        "test('mutates lock', () => { appendFileSync('package-lock.json', ' '); "
        "expect(1).toBe(1); });"
    )
    receipt = vitest_project.capture()
    capture = json.loads((receipt.parent / "capture.json").read_text())
    assert capture["exit_code"] == 0
    assert capture["before"] != capture["after"]
    result = verify_execution_observation(receipt, vitest_project.root, FEATURE, "passed")
    print(json.dumps({"case": "during-run lock drift", "gaps": result.gaps}))
    assert not result.valid
    assert "Execution inputs changed during invocation" in result.gaps


@pytest.mark.parametrize(
    "field,value",
    [("path", "never-loaded.ts"), ("test_id", "foreign::test")],
    ids=["source-path", "foreign-test-id"],
)
def test_rebound_trace_cannot_claim_a_foreign_assertion_origin(
    vitest_project: VitestProject, field: str, value: str
) -> None:
    """Reject mismatched test/source attribution independently of trace hash tamper checks."""
    vitest_project.write(PASSING)
    receipt = vitest_project.capture()
    assert verify_execution_observation(receipt, vitest_project.root, FEATURE, "passed").valid
    trace = json.loads((receipt.parent / "assertions").read_text())
    trace["assertions"][0][field] = value
    _rebind_trace(vitest_project, receipt, json.dumps(trace).encode())
    result = verify_execution_observation(receipt, vitest_project.root, FEATURE, "passed")
    print(json.dumps({"case": field, "gaps": result.gaps}))
    assert not result.valid
    assert any("origin" in gap or "matcher" in gap for gap in result.gaps), result.gaps


def test_current_owned_hook_substitution_is_rejected_without_mutating_shared_assets(
    vitest_project: VitestProject, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Recheck a fixture-local owned hook copy while leaving production assets untouched."""
    root = vitest_project.root
    copied_validator = root / "owned-runtime/validator"
    assets = copied_validator / "vitest"
    shutil.copytree(Path(execution_vitest.__file__).with_name("vitest"), assets)
    # Both locators must select the same isolated assets during preparation and reverification.
    monkeypatch.setattr(execution_vitest, "__file__", str(copied_validator / "execution_vitest.py"))
    monkeypatch.setattr(
        execution_vitest_provenance,
        "__file__",
        str(copied_validator / "execution_vitest_provenance.py"),
    )
    vitest_project.write(PASSING)
    receipt = vitest_project.capture()
    before = verify_execution_observation(receipt, root, FEATURE, "passed")
    assert before.valid, before.gaps
    hook = assets / "matcher-observer.ts"
    hook.write_text(hook.read_text() + "\n// fixture-only changed hook\n")
    result = verify_execution_observation(receipt, root, FEATURE, "passed")
    print(json.dumps({"case": "owned hook copy drift", "gaps": result.gaps}))
    assert not result.valid
    assert "Trusted runner provenance changed or missing" in result.gaps
