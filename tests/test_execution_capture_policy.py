"""Historical runner bytes remain readable without becoming current execution proof."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.execution_evidence_support import AC, FEATURE, run
from tests.execution_evidence_support import project as project
from validator.execution_capture import ExecutionCapture
from validator.execution_evidence import verify_execution_observation, verify_execution_receipt


def _historical_run(root: Path, monkeypatch: pytest.MonkeyPatch, policy: str | None) -> Path:
    """Exercise the real runner with the historical serializer at its publication boundary."""
    original = ExecutionCapture.model_dump_json

    def serialize(capture: ExecutionCapture, *, indent: int | None = None) -> str:
        if policy is None:
            return original(capture, indent=indent, exclude={"acceptance_evidence_policy"})
        historical = capture.model_copy(update={"acceptance_evidence_policy": policy})
        return original(historical, indent=indent)

    with monkeypatch.context() as scoped:
        scoped.setattr(ExecutionCapture, "model_dump_json", serialize)
        return run(root)


@pytest.mark.parametrize("historical_policy", [None, "1"])
def test_identical_sources_require_a_new_current_runner_capture(
    project: Path, monkeypatch: pytest.MonkeyPatch, historical_policy: str | None
) -> None:
    old = _historical_run(project, monkeypatch, historical_policy)
    old_bytes = (old.parent / "capture.json").read_bytes()
    historical = ExecutionCapture.model_validate_json(old_bytes)
    assert historical.acceptance_evidence_policy == "1"
    assert verify_execution_receipt(old, project, FEATURE, (AC,), evidence_policy="1").valid
    rejected = verify_execution_receipt(old, project, FEATURE, (AC,))
    assert not rejected.valid and not rejected.certified_acs
    assert any("acceptance evidence policy 2" in gap for gap in rejected.gaps)
    assert verify_execution_observation(old, project, FEATURE, "passed", evidence_policy="1").valid
    assert not verify_execution_observation(old, project, FEATURE, "passed").valid
    current = run(project)
    captured = ExecutionCapture.model_validate_json((current.parent / "capture.json").read_bytes())
    assert captured.acceptance_evidence_policy == "2"
    assert historical.after == captured.before == captured.after
    assert verify_execution_receipt(current, project, FEATURE, (AC,)).certified_acs == [AC]
    assert (old.parent / "capture.json").read_bytes() == old_bytes


def test_unknown_runner_policy_cannot_certify_current_acceptance(
    project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    receipt = _historical_run(project, monkeypatch, "future")
    rejected = verify_execution_receipt(receipt, project, FEATURE, (AC,))
    assert not rejected.valid and not rejected.certified_acs
    assert any("acceptance evidence policy 2" in gap for gap in rejected.gaps)


def test_unknown_runner_policy_is_not_a_historical_capture(
    project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    receipt = _historical_run(project, monkeypatch, "future")
    historical = verify_execution_receipt(receipt, project, FEATURE, (AC,), evidence_policy="1")
    assert not historical.valid and not historical.certified_acs
    assert any("Unsupported runner" in gap for gap in historical.gaps)
    observation = verify_execution_observation(
        receipt, project, FEATURE, "passed", evidence_policy="1"
    )
    assert not observation.valid and not observation.certified_acs


def test_runner_policy_is_bound_to_the_published_capture_hash(project: Path) -> None:
    receipt = run(project)
    assert verify_execution_receipt(receipt, project, FEATURE, (AC,)).valid
    path = receipt.parent / "capture.json"
    capture = json.loads(path.read_bytes())
    capture["acceptance_evidence_policy"] = "1"
    path.chmod(0o600)
    path.write_text(json.dumps(capture))
    rejected = verify_execution_receipt(receipt, project, FEATURE, (AC,))
    assert not rejected.valid and not rejected.certified_acs
    assert any("Runner capture changed" in gap for gap in rejected.gaps)


def test_old_failed_assertion_remains_red_only_for_its_historical_policy(
    project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (project / "app.py").write_text("def add(a, b):\n    return 0\n")
    receipt = _historical_run(project, monkeypatch, None)
    historical = verify_execution_observation(receipt, project, FEATURE, "red", evidence_policy="1")
    assert historical.valid and not historical.certified_acs
    assert any(
        test.status == "failed" and test.assertion_count for test in historical.executed_tests
    )
    current = verify_execution_observation(receipt, project, FEATURE, "red")
    assert not current.valid and not current.certified_acs
    assert any("acceptance evidence policy 2" in gap for gap in current.gaps)
