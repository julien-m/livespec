"""Real Vitest matcher execution, complete selection, provenance and observation limits."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Literal

import pytest

from tests.execution_vitest_fixture import FEATURE, VitestProject
from tests.execution_vitest_fixture import vitest_dependencies as vitest_dependencies
from tests.execution_vitest_fixture import vitest_project as vitest_project
from validator.execution_capture import capture_execution
from validator.execution_evidence import (
    EvidenceVerification,
    verify_execution_observation,
    verify_execution_receipt,
)

pytestmark = pytest.mark.integration


def _observe(
    project: VitestProject, receipt: Path, outcome: Literal["passed", "red"]
) -> EvidenceVerification:
    return verify_execution_observation(receipt, project.root, FEATURE, outcome)


@pytest.mark.parametrize("expected,outcome", [(1, "passed"), (2, "red")])
def test_real_sync_matcher_observes_outcome_without_certifying_acceptance(
    vitest_project: VitestProject, expected: int, outcome: Literal["passed", "red"]
) -> None:
    """Verify real synchronous matcher outcomes without feature acceptance."""
    source = vitest_project.write(f"test('sum', () => {{ expect(1).toBe({expected}); }});")
    receipt = vitest_project.capture()
    observed = _observe(vitest_project, receipt, outcome)
    # @spec AC-001: Genuine direct local execution produces a verified observation.
    # — .specs/features/096-node-vitest-execution/spec.md#ac-001
    assert observed.valid, observed.gaps
    assert observed.certified_acs == []
    assert len(observed.executed_tests) == 1
    assertions = json.loads((receipt.parent / "assertions").read_text())["assertions"]
    assert len(assertions) == 1
    assert assertions[0]["line"] == 2
    assert assertions[0]["path"] == str(source.relative_to(vitest_project.root))
    assert assertions[0]["status"] == ("passed" if outcome == "passed" else "failed")
    assert not _observe(vitest_project, receipt, "red" if outcome == "passed" else "passed").valid
    # @spec AC-005: Observation evidence never certifies feature acceptance.
    # — .specs/features/096-node-vitest-execution/spec.md#ac-005
    assert not verify_execution_receipt(receipt, vitest_project.root, FEATURE).valid


@pytest.mark.parametrize(
    "source",
    [
        "test('bare', () => { expect(1); });",
        "test('empty', () => {});",
        "test.skip('skipped', () => { expect(1).toBe(1); });",
        "test('good', () => { expect(1).toBe(1); }); test('empty', () => {});",
        "// Deliberately no collected tests.",
    ],
    ids=["bare-expect", "no-assertion", "skip-only", "mixed-empty", "zero-tests"],
)
def test_every_selected_test_requires_an_executed_matcher(
    vitest_project: VitestProject, source: str
) -> None:
    """Reject empty, bare, skipped and partially observed selections."""
    vitest_project.write(source)
    receipt = vitest_project.capture()
    for outcome in ("passed", "red"):
        result = _observe(vitest_project, receipt, outcome)
        assert not result.valid
        assert result.gaps


@pytest.mark.parametrize(
    "prefix,expression,expected,outcome,qualifies",
    [
        ("await ", "Promise.resolve(1)).resolves", 1, "passed", True),
        ("return ", "Promise.resolve(1)).resolves", 2, "red", True),
        ("", "Promise.resolve(1)).resolves", 1, "passed", False),
        ("", "Promise.resolve(1)).resolves", 2, "red", False),
        ("await ", "Promise.reject(1)).rejects", 1, "passed", True),
        ("return ", "Promise.reject(1)).rejects", 2, "red", True),
        ("", "Promise.reject(1)).rejects", 1, "passed", False),
        ("", "Promise.reject(1)).rejects", 2, "red", False),
    ],
)
def test_async_matcher_requires_consumer_await_or_return_not_vitest_autoawait(
    vitest_project: VitestProject,
    prefix: str,
    expression: str,
    expected: int,
    outcome: Literal["passed", "red"],
    qualifies: bool,
) -> None:
    """Distinguish explicit async consumption from framework automatic awaiting."""
    vitest_project.write(
        f"test('async assertion', async () => {{ {prefix}expect({expression}.toBe({expected}); }});"
    )
    receipt = vitest_project.capture()
    observed = _observe(vitest_project, receipt, outcome)
    # @spec AC-002: Real matcher settlement also requires explicit async consumption.
    # — .specs/features/096-node-vitest-execution/spec.md#ac-002
    assert observed.valid is qualifies, observed.gaps
    if not qualifies:
        assert any("consum" in gap.lower() or "await" in gap.lower() for gap in observed.gaps)


@pytest.mark.parametrize(
    "source",
    [
        "expect.extend({ toBeCustom: () => ({pass:true,message:()=>''}) }); "
        "test('custom', () => { expect(1).toBeCustom(); });",
        "test.concurrent('concurrent', () => { expect(1).toBe(1); });",
        "test('chai', () => { chai.expect(1).to.equal(1); });",
    ],
    ids=["custom", "concurrent", "direct-chai"],
)
def test_unsupported_selected_assertion_paths_fail_closed(
    vitest_project: VitestProject, source: str
) -> None:
    """Reject custom, concurrent and direct Chai assertion execution."""
    vitest_project.write(source)
    result = _observe(vitest_project, vitest_project.capture(), "passed")
    assert not result.valid
    assert result.gaps


def test_original_config_selection_setup_and_teardown_are_preserved(
    vitest_project: VitestProject,
) -> None:
    """Preserve original configuration environment, selection and lifecycle hooks."""
    root = vitest_project.root
    (root / "vitest.config.ts").write_text(
        "export default ({mode, command}) => {\n"
        "if(mode !== 'test' || command !== 'serve') throw Error('wrong config env');\n"
        "return {test:{include:['selected.test.ts'], setupFiles:['./setup.ts'], "
        "maxWorkers:1,minWorkers:1}}; };\n"
    )
    (root / "setup.ts").write_text(
        "import {afterEach, expect} from 'vitest';\n"
        "globalThis.fixtureConfigured = true;\n"
        "afterEach(() => { expect(globalThis.fixtureConfigured).toBe(true); });\n"
    )
    vitest_project.write(
        "test('configured', () => { expect(globalThis.fixtureConfigured).toBe(true); });",
        "selected.test.ts",
    )
    vitest_project.write("throw Error('must remain excluded');", "excluded.test.ts")
    receipt = vitest_project.capture()
    result = _observe(vitest_project, receipt, "passed")
    assert result.valid, result.gaps
    assert len(result.executed_tests) == 1
    assertions = json.loads((receipt.parent / "assertions").read_text())["assertions"]
    assert {item["path"] for item in assertions} == {"selected.test.ts", "setup.ts"}


def test_teardown_failure_is_finalized_as_real_red(vitest_project: VitestProject) -> None:
    """Include failing teardown matchers in the finalized test outcome."""
    vitest_project.write(
        "afterEach(() => { expect(1).toBe(2); });\n"
        "test('body passes', () => { expect(1).toBe(1); });"
    )
    receipt = vitest_project.capture()
    result = _observe(vitest_project, receipt, "red")
    assert result.valid, result.gaps
    assertions = json.loads((receipt.parent / "assertions").read_text())["assertions"]
    assert {item["status"] for item in assertions} == {"passed", "failed"}


@pytest.mark.parametrize(
    "changed", ["package-lock.json", "vitest.config.ts", "node_modules/vitest/vitest.mjs"]
)
def test_current_lock_config_and_runtime_bytes_are_rechecked(
    vitest_project: VitestProject, changed: str
) -> None:
    """Reject current input bytes that differ from the captured invocation."""
    vitest_project.write("test('passes', () => { expect(1).toBe(1); });")
    receipt = vitest_project.capture()
    before = _observe(vitest_project, receipt, "passed")
    assert before.valid, before.gaps
    path = vitest_project.root / changed
    path.write_text(path.read_text() + "\n ")
    # @spec AC-003: Reverification binds current lock, config and installed runtime bytes.
    # — .specs/features/096-node-vitest-execution/spec.md#ac-003
    result = _observe(vitest_project, receipt, "passed")
    assert not result.valid
    assert any("changed" in gap.lower() for gap in result.gaps), result.gaps


@pytest.mark.parametrize("artifact", ["report", "assertions", "inventory"])
def test_artifact_tampering_cannot_reuse_a_passing_receipt(
    vitest_project: VitestProject, artifact: str
) -> None:
    """Reject mutated report, assertion and inventory artifacts."""
    vitest_project.write("test('passes', () => { expect(1).toBe(1); });")
    receipt = vitest_project.capture()
    assert _observe(vitest_project, receipt, "passed").valid
    path = receipt.parent / artifact
    vitest_project.replace_artifact(receipt, artifact, path.read_bytes() + b" ")
    assert not _observe(vitest_project, receipt, "passed").valid


def test_foreign_invocation_artifacts_cannot_be_replayed(vitest_project: VitestProject) -> None:
    """Reject an inventory copied from another genuine invocation."""
    vitest_project.write("test('passes', () => { expect(1).toBe(1); });")
    first = vitest_project.capture()
    second = vitest_project.capture()
    assert first.parent != second.parent
    first_capture = json.loads((first.parent / "capture.json").read_text())
    second_capture = json.loads((second.parent / "capture.json").read_text())
    assert first_capture["invocation"] != second_capture["invocation"]
    vitest_project.replace_inventory(second, (first.parent / "inventory").read_bytes())
    result = _observe(vitest_project, second, "passed")
    assert not result.valid
    assert any("Foreign Vitest inventory" in gap for gap in result.gaps), result.gaps


def test_runner_owned_unknown_and_escaping_arguments_are_rejected(
    vitest_project: VitestProject,
) -> None:
    """Reject unsupported flags and escaping paths before execution."""
    vitest_project.write("test('passes', () => { expect(1).toBe(1); });")
    for arguments in (
        ("--watch",),
        ("--reporter", "default"),
        ("--pool", "threads"),
        ("--workspace", "workspace.ts"),
        ("--unknown-argument",),
        ("../escaped.test.ts",),
        ("--root", ".."),
        ("--testNamePattern",),
    ):
        with pytest.raises(ValueError) as rejected:
            vitest_project.capture(*arguments)
        assert "Vitest" in str(rejected.value)


def test_node_loading_overrides_are_rejected(vitest_project: VitestProject) -> None:
    """Reject caller options that replace Node module loading."""
    vitest_project.write("test('passes', () => { expect(1).toBe(1); });")
    with pytest.raises(ValueError, match="NODE_OPTIONS") as rejected:
        capture_execution(
            vitest_project.command(),
            project_root=vitest_project.root,
            feature=FEATURE,
            adapter="junit",
            env={**os.environ, "NODE_OPTIONS": "--no-warnings"},
            timeout=10,
        )
    assert "NODE_OPTIONS" in str(rejected.value)


def test_runtime_deadline_cannot_qualify_as_a_matcher_red(vitest_project: VitestProject) -> None:
    """Reject timeout evidence for both passing and red observation purposes."""
    vitest_project.write(
        "test('never settles', async () => { expect(1).toBe(1); await new Promise(() => {}); });"
    )
    receipt = vitest_project.capture(timeout=1.5)
    capture = json.loads((receipt.parent / "capture.json").read_text())
    # @spec AC-004: The shared hard cap includes setup and runtime; timeout never qualifies.
    # — .specs/features/096-node-vitest-execution/spec.md#ac-004
    assert capture["exit_code"] == 124
    assert capture["budget"]["timed_out"]
    assert not _observe(vitest_project, receipt, "red").valid
    assert not _observe(vitest_project, receipt, "passed").valid


def test_duplicate_selected_identity_is_rejected_even_with_rebound_hashes(
    vitest_project: VitestProject,
) -> None:
    """Reject ambiguous duplicate inventory identities independently of artifact hashing."""
    vitest_project.write("test('passes', () => { expect(1).toBe(1); });")
    receipt = vitest_project.capture()
    inventory = json.loads((receipt.parent / "inventory").read_text())
    inventory["tests"].append(inventory["tests"][0])
    vitest_project.replace_inventory(receipt, json.dumps(inventory).encode())
    result = _observe(vitest_project, receipt, "passed")
    assert not result.valid
    assert any("inventory mismatch" in gap for gap in result.gaps), result.gaps


def test_ignored_transitive_config_import_remains_bound(vitest_project: VitestProject) -> None:
    """Bind a loaded local config import even when ordinary discovery ignores it."""
    root = vitest_project.root
    ignored = root / "ignored-config.ts"
    ignored.write_text("export default {test:{maxWorkers:1,minWorkers:1}};")
    (root / ".gitignore").write_text("ignored-config.ts\n")
    (root / "vitest.config.ts").write_text(
        "import config from './ignored-config'; export default config;"
    )
    vitest_project.write("test('passes', () => { expect(1).toBe(1); });")
    receipt = vitest_project.capture()
    result = _observe(vitest_project, receipt, "passed")
    assert result.valid, result.gaps
    inventory = json.loads((receipt.parent / "inventory").read_text())
    assert "ignored-config.ts" in inventory["bound_inputs"]
    ignored.write_text(ignored.read_text() + "\n ")
    assert not _observe(vitest_project, receipt, "passed").valid
