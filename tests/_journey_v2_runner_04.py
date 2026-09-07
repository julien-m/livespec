"""Preserved test cases and fixtures for test_journey_v2_runner.py."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Unpack

import pytest

from tests._journey_v2_runner_01 import _RunKwargs, _setup_compiled
from tests.test_journey_v2_validation import _write_feature, _write_v2_journey
from validator.journeys.compiler import compile_journeys
from validator.journeys.runner import run_journeys


def test_run_journeys_ignores_prefix_on_passing_run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Edge case: stray prefix text in a passing run changes nothing."""
    _setup_compiled(tmp_path)

    def fake_run(
        argv: list[str],
        **_kwargs: Unpack[_RunKwargs],
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            argv,
            0,
            stdout="log noise JOURNEY_BOOTSTRAP_FAILURE: not a real failure",
            stderr="",
        )

    monkeypatch.setattr("validator.journeys.runner.subprocess.run", fake_run)

    result = run_journeys(tmp_path, journey="onboarding-first-project")

    assert result.error_count == 0, [issue.code for issue in result.issues]
    assert result.executed == ["onboarding-first-project"]


def test_run_journeys_fails_stale_contract_hash_without_recompiling(tmp_path: Path) -> None:
    """AC-009: a fixtures.yaml change after compilation marks artifacts stale."""
    specs = _setup_compiled(tmp_path)
    contract_path = specs / "journeys" / "fixtures.yaml"
    contract_path.write_text("schema_version: 1\n", encoding="utf-8")

    result = run_journeys(tmp_path, journey="onboarding-first-project", execute=False)

    assert result.error_count == 1
    assert result.issues[0].code == "journey_compiled_stale"
    assert "fixtures contract" in result.issues[0].message


def test_run_journeys_fails_when_contract_deleted_after_compile(tmp_path: Path) -> None:
    """AC-009: deleting the contract after compile is a hash mismatch."""
    specs = tmp_path / ".specs"
    specs.mkdir()
    _write_feature(specs, "001-onboarding")
    _write_feature(specs, "012-projects")
    _write_v2_journey(specs)
    contract_path = specs / "journeys" / "fixtures.yaml"
    contract_path.write_text("schema_version: 1\n", encoding="utf-8")
    compile_result = compile_journeys(tmp_path, journey="onboarding-first-project")
    assert compile_result.error_count == 0
    contract_path.unlink()

    result = run_journeys(tmp_path, journey="onboarding-first-project", execute=False)

    assert result.error_count == 1
    assert result.issues[0].code == "journey_compiled_stale"


def test_run_journeys_reports_compiler_stale_before_contract_hash(tmp_path: Path) -> None:
    """AC-008: pre-v2-3 manifests report journey_compiler_stale, never a hash mismatch."""
    specs = _setup_compiled(tmp_path)
    manifest_path = specs / "journeys" / "onboarding-first-project" / "compiled" / "manifest.json"
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    data["compiler_version"] = "journeys-v2-2"
    # Tolerant reader: pre-060 manifests have no fixtures_contract_hash field.
    data.pop("fixtures_contract_hash", None)
    manifest_path.write_text(json.dumps(data), encoding="utf-8")
    (specs / "journeys" / "fixtures.yaml").write_text("schema_version: 1\n", encoding="utf-8")

    result = run_journeys(tmp_path, journey="onboarding-first-project", execute=False)

    assert result.error_count == 1
    assert result.issues[0].code == "journey_compiler_stale"
