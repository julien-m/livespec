"""Real pytest protocol fixtures and frozen category/exception boundaries."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

from tests.execution_cargo_support import FEATURE as CARGO_FEATURE
from tests.execution_cargo_support import cargo_env
from tests.execution_cargo_support import crate as crate
from validator import test_budgets
from validator.execution_capture import capture_execution
from validator.execution_deadline import command_scope
from validator.execution_evidence import verify_execution_receipt
from validator.execution_test_budget import resolve_test_budget
from validator.test_budgets import BudgetPolicy

pytestmark = pytest.mark.integration


def _run(root: Path, source: str):
    (root / "test_case.py").write_text(source)
    (root / ".specs/features/001-case").mkdir(parents=True, exist_ok=True)
    (root / ".specs/features/001-case/spec.md").write_text("# Feature\n")
    return capture_execution(
        [sys.executable, "-m", "pytest", "-q", "test_case.py"],
        project_root=root,
        feature="001-case",
        adapter="junit",
        env={**os.environ, "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1"},
        timeout=3,
    )


@pytest.mark.parametrize("phase", ["setup", "call", "teardown"])
def test_pytest_hung_lifecycle_stops_without_assertion_red(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, phase: str
) -> None:
    # Inject a short native unit allowance into the frozen policy; no minutes-long wait.
    monkeypatch.setitem(
        __import__(
            "validator.test_budgets", fromlist=["DEFAULT_TEST_SECONDS"]
        ).DEFAULT_TEST_SECONDS,
        "unit",
        0.15,
    )
    source = "import time,pytest\n@pytest.fixture\ndef resource():\n"
    source += "    time.sleep(5)\n" if phase == "setup" else "    pass\n"
    source += "    yield\n"
    source += "    time.sleep(5)\n" if phase == "teardown" else "    pass\n"
    source += "def test_case(resource):\n" + (
        "    time.sleep(5)\n" if phase == "call" else "    assert True\n"
    )
    result = _run(tmp_path, source)
    assert result.exit_code == 124, result.stderr
    assert "LIVESPEC_TEST_TIMEOUT" in result.stderr
    verified = verify_execution_receipt(Path(result.receipt_path), tmp_path, "001-case")
    assert not verified.valid and not verified.certified_acs


def test_frozen_category_defaults_and_exact_exception() -> None:
    policy = BudgetPolicy().frozen(["pytest"], 300)
    # @spec AC-002: Frozen category limits
    # — .specs/features/095-test-time-budgets/spec.md#ac-002
    assert [
        resolve_test_budget(policy, "x", category)["test_seconds"]
        for category in ("unit", "integration", "acceptance")
    ] == [2, 10, 30]
    policy["exceptions"] = [
        {
            "test": "a::b",
            "test_seconds": 100,
            "category": "benchmark",
            "id": "big",
            "reason": "capacity",
        }
    ]
    assert resolve_test_budget(policy, "a::b", "unit")["test_seconds"] == 100
    assert resolve_test_budget(policy, "a::other", "unit")["test_seconds"] == 2


def test_supported_pytest_pass_and_unknown_command_granularity(tmp_path: Path) -> None:
    result = _run(tmp_path, "def test_case():\n    assert 2 + 2 == 4\n")
    capture = json.loads((Path(result.receipt_path).parent / "capture.json").read_text())
    assert result.exit_code == 0, result.stderr
    assert capture["budget"]["enforcement"] == "individual-and-command"
    with command_scope(tmp_path, ["unknown"]) as scope:
        assert scope.evidence()["enforcement"] == "command-only"


def test_real_cargo_exact_test_timeout(crate: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """One tiny actual Cargo target proves the hook propagates a timeout as exit 124."""
    monkeypatch.setitem(test_budgets.DEFAULT_TEST_SECONDS, "integration", 0.15)
    (crate / "tests/integ.rs").write_text(
        "#[test] fn integration_adds() {\n"
        "std::thread::sleep(std::time::Duration::from_secs(5)); }\n"
    )
    result = capture_execution(
        ["cargo", "test", "--test", "integ"],
        project_root=crate,
        feature=CARGO_FEATURE,
        adapter="junit",
        env=cargo_env(crate),
        timeout=10,
    )
    assert result.exit_code == 124, result.stderr
    assert "LIVESPEC_TEST_TIMEOUT" in result.stderr
    assert not verify_execution_receipt(Path(result.receipt_path), crate, CARGO_FEATURE).valid
