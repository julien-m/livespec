"""Real Vitest regressions for alternate contexts, nested dispatch and retry integrity."""

from __future__ import annotations

import json
from typing import Literal

import pytest

from tests.execution_vitest_fixture import FEATURE, VitestProject
from tests.execution_vitest_fixture import vitest_dependencies as vitest_dependencies
from tests.execution_vitest_fixture import vitest_project as vitest_project
from validator.execution_evidence import verify_execution_observation

pytestmark = pytest.mark.integration


@pytest.mark.parametrize(
    "body",
    [
        "local.extend({toBeCustom:()=>({pass:true,message:()=>''})}); local(1).toBeCustom();",
        "await local.poll(() => 1).toBe(1);",
        "local.soft(1).toBe(1);",
        "local.addEqualityTesters([() => true]); local(1).toEqual(2);",
    ],
    ids=["extend", "poll", "soft", "equality-testers"],
)
def test_context_expect_unsupported_forms_cannot_hide_behind_a_supported_matcher(
    vitest_project: VitestProject, body: str
) -> None:
    """Reject unsupported local expect semantics even alongside a genuine built-in assertion."""
    vitest_project.write(
        "test('alternate context', async ({expect: local}) => { " + body + " expect(1).toBe(1); });"
    )
    receipt = vitest_project.capture()
    result = verify_execution_observation(receipt, vitest_project.root, FEATURE, "passed")
    assert not result.valid, "Unsupported context.expect qualified a passing observation"
    assert any("Unsupported" in gap for gap in result.gaps), result.gaps


@pytest.mark.parametrize("form", ["resolves", "rejects"])
@pytest.mark.parametrize("consumed", [True, False], ids=["awaited", "unawaited"])
def test_negated_async_chain_retains_consumption_tracking(
    vitest_project: VitestProject, form: Literal["resolves", "rejects"], consumed: bool
) -> None:
    """Accept awaited negation and reject automatic awaiting despite another real matcher."""
    promise = "resolve" if form == "resolves" else "reject"
    prefix = "await " if consumed else ""
    vitest_project.write(
        "test('negated async', async () => { "
        f"{prefix}expect(Promise.{promise}(1)).{form}.not.toBe(2); "
        "expect(1).toBe(1); });"
    )
    receipt = vitest_project.capture()
    result = verify_execution_observation(receipt, vitest_project.root, FEATURE, "passed")
    assert result.valid is consumed, result.gaps
    if consumed:
        assertions = json.loads((receipt.parent / "assertions").read_text())["assertions"]
        assert len(assertions) == 2
    else:
        assert any("consum" in gap.lower() for gap in result.gaps), result.gaps


@pytest.mark.parametrize(
    "nested",
    [
        "expect(Promise.resolve(1)).resolves.toBe(1);",
        "chai.expect(1).to.equal(1);",
    ],
    ids=["unawaited-async", "direct-chai"],
)
def test_nested_user_callback_cannot_inherit_framework_dispatch_exemption(
    vitest_project: VitestProject, nested: str
) -> None:
    """Reject unsupported consumer assertions executed inside a supported toThrow callback."""
    vitest_project.write(
        "test('nested consumer callback', () => { expect(() => { "
        + nested
        + " throw Error('outer'); }).toThrow('outer'); });"
    )
    receipt = vitest_project.capture()
    inventory = json.loads((receipt.parent / "inventory").read_text())
    assert len(inventory["tests"]) == 1, "A collection failure is not nested-dispatch refusal"
    result = verify_execution_observation(receipt, vitest_project.root, FEATURE, "passed")
    assert not result.valid, "Nested consumer assertion bypassed observation guards"
    assert result.gaps


def test_retry_cannot_erase_an_unconsumed_assertion_from_an_earlier_attempt(
    vitest_project: VitestProject,
) -> None:
    """Reject retry success when the earlier real attempt used an unsupported async assertion."""
    vitest_project.write(
        "let attempts = 0;\n"
        "test('retry', () => { attempts++; if (attempts === 1) { "
        "expect(Promise.resolve(1)).resolves.toBe(1); throw Error('retry me'); } "
        "expect(1).toBe(1); }, {retry: 1});"
    )
    receipt = vitest_project.capture()
    capture = json.loads((receipt.parent / "capture.json").read_text())
    assert capture["exit_code"] == 0
    result = verify_execution_observation(receipt, vitest_project.root, FEATURE, "passed")
    assert not result.valid, "A successful retry erased unsupported earlier-attempt evidence"
    assert any("consum" in gap.lower() for gap in result.gaps), result.gaps


def test_context_guard_preserves_global_assertion_counting(vitest_project: VitestProject) -> None:
    """Keep global expect.assertions working with Vitest requireAssertions enabled."""
    (vitest_project.root / "vitest.config.ts").write_text(
        "export default {test:{maxWorkers:1,minWorkers:1,expect:{requireAssertions:true}}};"
    )
    vitest_project.write(
        "test('global assertion counts', () => { expect.assertions(1); expect(1).toBe(1); });"
    )
    receipt = vitest_project.capture()
    result = verify_execution_observation(receipt, vitest_project.root, FEATURE, "passed")
    assert result.valid, result.gaps


def test_supported_nested_callback_matchers_remain_observable(
    vitest_project: VitestProject,
) -> None:
    """Record both supported assertions when consumer code runs inside a toThrow callback."""
    vitest_project.write(
        "test('nested supported', () => { expect(() => { expect(1).toBe(1); "
        "throw Error('outer'); }).toThrow('outer'); });"
    )
    receipt = vitest_project.capture()
    result = verify_execution_observation(receipt, vitest_project.root, FEATURE, "passed")
    assert result.valid, result.gaps
    assertions = json.loads((receipt.parent / "assertions").read_text())["assertions"]
    assert len(assertions) == 2


def test_supported_failed_retry_attempt_does_not_override_final_success(
    vitest_project: VitestProject,
) -> None:
    """Allow a genuine successful retry when earlier assertions were supported and settled."""
    vitest_project.write(
        "let attempts = 0; test('supported retry', () => { "
        "expect(++attempts).toBe(2); }, {retry: 1});"
    )
    receipt = vitest_project.capture()
    result = verify_execution_observation(receipt, vitest_project.root, FEATURE, "passed")
    assert result.valid, result.gaps
    assertions = json.loads((receipt.parent / "assertions").read_text())["assertions"]
    assert len(assertions) == 1
    assert assertions[0]["status"] == "passed"


def test_setup_failure_without_a_matcher_cannot_qualify_as_red(
    vitest_project: VitestProject,
) -> None:
    """Reject setup-only failure even when the selected test body contains a real matcher."""
    root = vitest_project.root
    (root / "vitest.config.ts").write_text(
        "export default {test:{maxWorkers:1,minWorkers:1,setupFiles:['./setup.ts']}};"
    )
    (root / "setup.ts").write_text("throw Error('setup failed before any matcher');")
    vitest_project.write("test('unreached body', () => { expect(1).toBe(1); });")
    receipt = vitest_project.capture()
    capture = json.loads((receipt.parent / "capture.json").read_text())
    assert capture["exit_code"] == 1
    assertions = json.loads((receipt.parent / "assertions").read_text())["assertions"]
    assert assertions == []
    for outcome in ("red", "passed"):
        result = verify_execution_observation(receipt, root, FEATURE, outcome)
        assert not result.valid, f"Setup-only failure qualified as {outcome}"


@pytest.mark.parametrize(
    "expression",
    [
        "assertion.then(() => {})",
        "Promise.resolve(assertion)",
        "Promise.all([assertion])",
        "Promise.race([assertion])",
    ],
    ids=["then", "resolve", "all", "race"],
)
def test_detached_async_consumption_cannot_qualify_as_awaited(
    vitest_project: VitestProject, expression: str
) -> None:
    """Reject detached chains even when native Promise assimilation consumes the thenable."""
    vitest_project.write(
        "test('detached', () => { const assertion = "
        "expect(Promise.resolve(1)).resolves.toBe(1); "
        f"{expression}; expect(1).toBe(1); }});"
    )
    receipt = vitest_project.capture()
    result = verify_execution_observation(receipt, vitest_project.root, FEATURE, "passed")
    assert not result.valid, result
    assert any("consum" in gap.lower() or "await" in gap.lower() for gap in result.gaps)


@pytest.mark.parametrize(
    "source,qualifies",
    [
        ("test('implicit', () => expect(Promise.resolve(1)).resolves.toBe(1));", True),
        (
            "import {it as caseTest} from 'vitest'; "
            "caseTest('alias', async () => { "
            "await expect(Promise.resolve(1)).resolves.toBe(1); });",
            True,
        ),
        (
            "test('nested', () => { const nested = () => { "
            "return expect(Promise.resolve(1)).resolves.toBe(1); }; "
            "Promise.resolve(nested()); expect(1).toBe(1); });",
            False,
        ),
        (
            "test('composition', async () => { "
            "await Promise.all([expect(Promise.resolve(1)).resolves.toBe(1)]); });",
            False,
        ),
        (
            "const identity = value => value; test('identity', () => { "
            "return identity(expect(Promise.resolve(1)).resolves.toBe(1)); });",
            False,
        ),
        (
            "test('sequence', () => { return (0, expect(Promise.resolve(1)).resolves.toBe(1)); });",
            False,
        ),
        (
            "test('discarded return', () => { try { "
            "return expect(Promise.resolve(1)).resolves.toBe(1); } finally { return; } });",
            False,
        ),
    ],
    ids=[
        "implicit-return",
        "import-alias",
        "detached-nested-return",
        "unsupported-composition",
        "unsupported-identity",
        "unsupported-sequence",
        "overridden-finally-return",
    ],
)
def test_async_source_proof_requires_direct_inline_test_ownership(
    vitest_project: VitestProject, source: str, qualifies: bool
) -> None:
    """Preserve direct syntax and aliases; nested returns and compositions fail closed."""
    vitest_project.write(source)
    receipt = vitest_project.capture()
    result = verify_execution_observation(receipt, vitest_project.root, FEATURE, "passed")
    assert result.valid is qualifies, result
