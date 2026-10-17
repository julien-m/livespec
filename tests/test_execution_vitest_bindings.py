"""Real async observations distinguish binding patterns from property keys/default values."""

from __future__ import annotations

import pytest

from tests.execution_vitest_fixture import FEATURE, VitestProject
from tests.execution_vitest_fixture import vitest_dependencies as vitest_dependencies
from tests.execution_vitest_fixture import vitest_project as vitest_project
from validator.execution_evidence import verify_execution_observation

pytestmark = pytest.mark.integration


@pytest.mark.parametrize(
    "declaration,consumption",
    [
        ("const {test: metadata} = {test: 1};", "await"),
        ("const {value: metadata = test} = {};", "return"),
        ("const [metadata = test] = [];", "await"),
        ("function helper(metadata = test) {}", "return"),
        ("function helper({test: metadata}) {}", "await"),
        ("try { throw {test: 1}; } catch ({test: metadata}) {}", "return"),
    ],
    ids=[
        "property-key",
        "property-default",
        "array-default",
        "parameter-default",
        "parameter-property-key",
        "catch-property-key",
    ],
)
def test_async_import_tracking_only_uses_pattern_bindings(
    vitest_project: VitestProject, declaration: str, consumption: str
) -> None:
    """Keep property keys and default expressions distinct from declared bindings."""
    vitest_project.write(
        declaration
        + " test('pattern ownership', async () => { "
        + consumption
        + " expect(Promise.resolve(1)).resolves.toBe(1); });"
    )
    receipt = vitest_project.capture()
    result = verify_execution_observation(receipt, vitest_project.root, FEATURE, "passed")
    assert result.valid, result.gaps


@pytest.mark.parametrize(
    "parameter,argument,callee",
    [
        ("{value: test}", "{value: test}", "test"),
        ("[test]", "[test]", "test"),
        ("test = () => {}", "test", "test"),
        ("{...test}", "{register: test}", "test.register"),
        ("[...test]", "[test]", "test[0]"),
    ],
    ids=[
        "object-shadow",
        "array-shadow",
        "default-left-shadow",
        "object-rest-shadow",
        "array-rest-shadow",
    ],
)
def test_async_registration_through_shadowed_parameter_fails_closed(
    vitest_project: VitestProject, parameter: str, argument: str, callee: str
) -> None:
    """Execute genuine registrations through shadowed parameters after Vite renaming."""
    vitest_project.write(
        f"function helper({parameter}) {{ {callee}('shadowed registration', async () => {{ "
        "await expect(Promise.resolve(1)).resolves.toBe(1); }); } "
        f"helper({argument});"
    )
    receipt = vitest_project.capture()
    result = verify_execution_observation(receipt, vitest_project.root, FEATURE, "passed")
    assert not result.valid, result.gaps
    assert any("consum" in gap.lower() or "await" in gap.lower() for gap in result.gaps)
