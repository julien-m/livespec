"""Real pytest protocol fixtures and frozen category/exception boundaries."""

from __future__ import annotations

import fcntl
import json
import os
import sys
import threading
import time
from pathlib import Path
from typing import NoReturn

import pytest
import typer
from typer.testing import CliRunner

from tests.execution_cargo_support import FEATURE as CARGO_FEATURE
from tests.execution_cargo_support import cargo_env
from tests.execution_cargo_support import crate as crate
from validator import execution_capture as capture_module
from validator import execution_evidence, test_budgets
from validator.cli import app
from validator.cli_commands import bugfix_cmd, execution_io
from validator.drivers.runner import run_capability
from validator.drivers.schemas import DriverCapability, DriverManifest
from validator.execution_capture import CaptureResult, capture_execution
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


def test_concurrent_publication_waits_and_expiry_closes_owned_descriptors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A temporary competing writer succeeds; a held lock times out without leaking descriptors."""
    from validator import execution_capture as capture_module

    specs = tmp_path / ".specs"
    specs.mkdir()
    held = os.open(specs, os.O_RDONLY | os.O_DIRECTORY)
    opened: list[int] = []
    original = capture_module._open_storage

    def tracking_open(root: Path) -> tuple[int, int]:
        pair = original(root)
        opened.extend(pair)
        return pair

    monkeypatch.setattr(capture_module, "_open_storage", tracking_open)
    try:
        fcntl.flock(held, fcntl.LOCK_EX)
        timer = threading.Timer(0.06, fcntl.flock, (held, fcntl.LOCK_UN))
        timer.start()
        result = capture_execution(
            [sys.executable, "-c", "pass"],
            project_root=tmp_path,
            feature="001-case",
            adapter="junit",
            env=dict(os.environ),
            timeout=0.6,
        )
        timer.join(timeout=1)
        assert result.exit_code == 0 and result.receipt_path
        fcntl.flock(held, fcntl.LOCK_EX)
        started = time.monotonic()
        result = capture_execution(
            [sys.executable, "-c", "pass"],
            project_root=tmp_path,
            feature="001-case",
            adapter="junit",
            env=dict(os.environ),
            timeout=0.15,
        )
        assert result.exit_code == 124 and not result.receipt_path
        assert time.monotonic() - started < 0.4
        for descriptor in opened:
            with pytest.raises(OSError):
                os.fstat(descriptor)
    finally:
        fcntl.flock(held, fcntl.LOCK_UN)
        os.close(held)


def test_no_fresh_receipt_remains_timeout_for_driver_cli_and_observation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Finalization exhaustion cannot turn an empty receipt into a directory inspection."""

    from validator import execution_capture as capture_module

    feature = tmp_path / ".specs/features/001-case"
    feature.mkdir(parents=True)
    (feature / "spec.md").write_text("# Timeout scope\n")
    with monkeypatch.context() as scoped:
        scoped.setattr(capture_module, "_publish", lambda *args: time.sleep(1))
        missing = capture_execution(
            [sys.executable, "-c", "pass"],
            project_root=tmp_path,
            feature="001-case",
            adapter="junit",
            env=dict(os.environ),
            timeout=0.12,
        )
    assert missing.exit_code == 124 and not missing.receipt_path

    _verify_missing_capture_consumers(tmp_path, monkeypatch, missing)


def _verify_missing_capture_consumers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, missing: CaptureResult
) -> None:
    """Exercise the three production consumers without allowing any absent-receipt inspection."""

    def fake_capture(*_args: object, **_kwargs: object) -> CaptureResult:
        return missing

    for owner in (capture_module, execution_io, bugfix_cmd):
        monkeypatch.setattr(owner, "capture_execution", fake_capture)

    def reject_inspection(*_args: object, **_kwargs: object) -> NoReturn:
        pytest.fail("Missing receipt must not be inspected")

    monkeypatch.setattr(execution_evidence, "verify_execution_receipt", reject_inspection)
    monkeypatch.setattr(execution_io, "verify_execution_receipt", reject_inspection)
    monkeypatch.setattr(bugfix_cmd, "observe", reject_inspection)
    driver = DriverManifest(
        name="python",
        snapshots=DriverCapability(command=f"{sys.executable} -c pass", report_adapter="junit"),
    )
    driven = run_capability(driver, "snapshots", project_root=tmp_path, feature="001-case")
    assert driven.exit_code == 124 and driven.certification_gaps
    with pytest.raises(typer.Exit) as stopped:
        execution_io._capture(
            tmp_path, "001-case", "python -c pass", tmp_path / "mapping.json", "junit"
        )
    assert stopped.value.exit_code == 124
    monkeypatch.chdir(tmp_path)
    observed = CliRunner().invoke(
        app,
        [
            "bugfix",
            "capture",
            "--feature",
            "001-case",
            "--expect",
            "green",
            "--command",
            "python -c pass",
            "--json",
        ],
    )
    assert observed.exit_code == 124, observed.output
    assert json.loads(observed.output)["observed"] is False
