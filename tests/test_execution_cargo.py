"""The trusted Cargo runner certifies real `cargo test` executions (feature 085)."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import pytest

from tests.execution_cargo_support import (
    AC,
    FEATURE,
    INTEGRATION_ID,
    capture,
    cargo_env,
    write_mapping,
)
from tests.execution_cargo_support import crate as crate
from validator import execution_evidence
from validator.execution_cargo_toolchain import CargoRunnerUnavailable
from validator.execution_evidence import verify_execution_observation, verify_execution_receipt

INTEGRATION = ["cargo", "test", "--test", "integ"]
LIB = ["cargo", "test", "--lib", "--no-fail-fast", "tests::"]


def _trace(receipt: Path) -> list[dict[str, Any]]:
    return json.loads((receipt.parent / "assertions").read_text())["assertions"]


def _capture_json(receipt: Path) -> dict[str, Any]:
    return json.loads((receipt.parent / "capture.json").read_text())


@pytest.mark.integration
def test_mapped_integration_assertion_is_certified(crate: Path) -> None:
    write_mapping(crate)
    receipt = capture(crate, INTEGRATION)
    result = verify_execution_receipt(receipt, crate, FEATURE, (AC,))
    assert result.valid, result.gaps
    assert result.certified_acs == [AC]
    [test] = result.executed_tests
    assert (test.test_id, test.status, test.assertion_count) == (INTEGRATION_ID, "passed", 1)
    [assertion] = _trace(receipt)
    assert assertion == {
        "test_id": INTEGRATION_ID,
        "path": str((crate / "tests/integ.rs").resolve()),
        "line": 4,
        "assertion": "assert_eq!(sum, 5)",
        "status": "passed",
    }
    assert _capture_json(receipt)["runner_provenance"]["runner"] == "cargo"


def test_bare_test_path_resolves_to_the_unique_binary(crate: Path) -> None:
    write_mapping(crate, test_id="integration_adds")
    result = verify_execution_receipt(capture(crate, INTEGRATION), crate, FEATURE, (AC,))
    assert result.valid and result.certified_acs == [AC], result.gaps


def test_binding_must_cite_one_complete_rust_assertion(crate: Path) -> None:
    with pytest.raises(ValueError, match="one complete assertion"):
        write_mapping(crate, line=3)  # `let sum = ...` is not an assertion.


def test_unreached_assertion_cannot_certify(crate: Path) -> None:
    passes = "fixture/lib/fixture::tests::passes"
    write_mapping(crate, test_id=passes, path="src/lib.rs", line=13)
    receipt = capture(crate, ["cargo", "test", "--lib", "tests::passes"])
    result = verify_execution_receipt(receipt, crate, FEATURE, (AC,))
    assert not result.valid
    assert f"Unproven acceptance binding: {AC} / {passes}" in result.gaps


def test_failed_ignored_and_filtered_tests_are_reported_faithfully(crate: Path) -> None:
    receipt = capture(crate, LIB, cargo_env(crate, LIVESPEC_FIXTURE_FLAG="1"))
    capture_data = _capture_json(receipt)
    assert capture_data["exit_code"] == 1
    report = ET.fromstring((receipt.parent / "report").read_bytes())
    statuses = {
        case.get("name"): "failed"
        if case.find("failure") is not None
        else ("skipped" if case.find("skipped") is not None else "passed")
        for case in report.iter("testcase")
    }
    assert statuses == {
        "tests::passes": "passed",
        "tests::fails": "failed",
        "tests::ignored": "skipped",
        "tests::reads_caller_environment": "passed",
    }
    filtered = [p.get("value") for p in report.iter("property") if p.get("name") == "filtered"]
    assert filtered == ["other::filtered_out"]
    observed = {(a["test_id"], a["line"], a["status"]) for a in _trace(receipt)}
    lib = "fixture/lib/fixture::tests::"
    assert observed == {
        (f"{lib}passes", 11, "passed"),
        (f"{lib}fails", 19, "failed"),
        (f"{lib}reads_caller_environment", 30, "passed"),
    }  # The unreachable assertion (line 13) and the ignored test leave no trace.
    red = verify_execution_observation(receipt, crate, FEATURE, "red")
    assert red.valid, red.gaps
    assert not verify_execution_receipt(receipt, crate, FEATURE).valid


def test_caller_environment_reaches_the_tests(crate: Path) -> None:
    command = ["cargo", "test", "--lib", "reads_caller_environment"]
    with_flag = capture(crate, command, cargo_env(crate, LIVESPEC_FIXTURE_FLAG="1"))
    without_flag = capture(crate, command)
    assert _capture_json(with_flag)["exit_code"] == 0
    assert _capture_json(without_flag)["exit_code"] == 1
    assert verify_execution_observation(with_flag, crate, FEATURE, "passed").valid


def test_doctests_outside_libtest_binaries_block_certification(crate: Path) -> None:
    lib = crate / "src/lib.rs"
    lib.write_text("/// ```\n/// assert_eq!(fixture::add(1, 1), 2);\n/// ```\n" + lib.read_text())
    receipt = capture(crate, ["cargo", "test", "--no-fail-fast"])
    gaps = _capture_json(receipt)["gaps"]
    assert "Runner: Doctests ran outside libtest binaries and cannot be traced" in gaps
    assert not verify_execution_receipt(receipt, crate, FEATURE).valid


def test_changed_runner_provenance_invalidates_the_capture(
    crate: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    write_mapping(crate)
    receipt = capture(crate, INTEGRATION)
    monkeypatch.setattr(execution_evidence, "current_cargo_provenance", lambda recorded: {})
    result = verify_execution_receipt(receipt, crate, FEATURE, (AC,))
    assert not result.valid
    assert "Trusted runner provenance changed or missing" in result.gaps


def test_missing_coverage_tools_still_run_but_cannot_certify(
    crate: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def unavailable(*_: object) -> dict[str, str]:
        raise CargoRunnerUnavailable("assertion tracing needs llvm-profdata and llvm-cov")

    monkeypatch.setattr("validator.execution_runner.cargo_provenance", unavailable)
    write_mapping(crate)
    receipt = capture(crate, INTEGRATION)
    capture_data = _capture_json(receipt)
    assert capture_data["exit_code"] == 0
    assert capture_data["argv"] == INTEGRATION
    assert capture_data["gaps"][0] == (
        "Unsupported runner: assertion tracing needs llvm-profdata and llvm-cov"
    )
    assert not verify_execution_receipt(receipt, crate, FEATURE, (AC,)).valid


def test_runner_owned_options_are_refused(crate: Path) -> None:
    with pytest.raises(ValueError, match="--no-run"):
        capture(crate, ["cargo", "test", "--no-run"])
    with pytest.raises(ValueError, match="RUSTC_WORKSPACE_WRAPPER"):
        capture(crate, INTEGRATION, cargo_env(crate, RUSTC_WORKSPACE_WRAPPER="/bin/echo"))


def test_build_failure_keeps_cargo_exit_code_and_reports_a_gap(crate: Path) -> None:
    (crate / "tests/integ.rs").write_text('#[test]\nfn broken() { let x: u8 = "no"; }\n')
    capture_data = _capture_json(capture(crate, INTEGRATION))
    assert capture_data["exit_code"] == 101
    assert "Runner: Cargo could not build the selected test binaries" in capture_data["gaps"]
