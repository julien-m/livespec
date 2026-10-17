"""Real late Chai/prototype extensions cannot hide behind an observed built-in matcher."""

from __future__ import annotations

import pytest

from tests.execution_vitest_fixture import FEATURE, VitestProject
from tests.execution_vitest_fixture import vitest_dependencies as vitest_dependencies
from tests.execution_vitest_fixture import vitest_project as vitest_project
from validator.execution_evidence import verify_execution_observation

pytestmark = pytest.mark.integration
_SET_WITNESS = "function(){globalThis.lateCustomExecuted=true;}"
_PLUGIN = "chai.use(api=>api.Assertion.addMethod('lateCustom'," + _SET_WITNESS + "));"


@pytest.mark.parametrize(
    "stage,registration,call",
    [
        ("setup", _PLUGIN, "expect(1).lateCustom();"),
        ("test", _PLUGIN, "expect(1).lateCustom();"),
        (
            "test",
            "Object.defineProperty(chai.Assertion.prototype,'lateCustom',"
            "{configurable:true,value:" + _SET_WITNESS + "});",
            "expect(1).lateCustom();",
        ),
        (
            "test",
            "Object.defineProperty(chai.Assertion.prototype,'lateCustom',"
            "{configurable:true,get:" + _SET_WITNESS + "});",
            "void expect(1).lateCustom;",
        ),
        (
            "test",
            "Object.defineProperty(chai.Assertion.prototype,'toBe',"
            "{configurable:true,value:" + _SET_WITNESS + "});",
            "expect(1).toBe(999);",
        ),
        (
            "test",
            "Object.setPrototypeOf(chai.Assertion.prototype,{lateCustom:" + _SET_WITNESS + "});",
            "expect(1).lateCustom();",
        ),
        (
            "test",
            "chai.util.addChainableMethod(chai.Assertion.prototype,'to',"
            + _SET_WITNESS
            + ",function(){});",
            "expect(1).to();",
        ),
    ],
    ids=[
        "plugin-setup",
        "plugin-test",
        "method",
        "getter",
        "replace-built-in",
        "parent",
        "chainable",
    ],
)
def test_late_custom_matcher_cannot_hide_behind_supported_dispatch(
    vitest_project: VitestProject, stage: str, registration: str, call: str
) -> None:
    """The custom operation must really run before the supported witness can pass on baseline."""
    if stage == "setup":
        (vitest_project.root / "vitest.config.ts").write_text(
            "export default {test:{maxWorkers:1,minWorkers:1,setupFiles:['./setup.ts']}};"
        )
        (vitest_project.root / "setup.ts").write_text("import {chai} from 'vitest';" + registration)
        registration = ""
    vitest_project.write(
        "test('late custom registration',()=>{"
        + registration
        + call
        + "expect(globalThis.lateCustomExecuted).toEqual(true);});"
    )
    receipt = vitest_project.capture()
    result = verify_execution_observation(receipt, vitest_project.root, FEATURE, "passed")
    assert not result.valid, "A late custom operation plus a genuine built-in matcher qualified"
    diagnostic = (receipt.parent / "stderr").read_text() + (
        receipt.parent / "runner-report"
    ).read_text()
    assert any(
        word in diagnostic.lower()
        for word in ("unsupported", "not extensible", "non-extensible", "redefine", "read only")
    ), diagnostic
