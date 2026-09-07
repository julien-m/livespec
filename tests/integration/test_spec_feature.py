"""Real production spec-feature pipeline plus a frozen behavioral acceptance oracle."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from tests.integration.helpers.witness_pipeline import run_pipeline_trial


@pytest.mark.level_3c
@pytest.mark.slow
def test_spec_feature_pipeline_produces_behavior_and_verified_closure(tmp_path: Path) -> None:
    if os.environ.get("LIVESPEC_REAL_PIPELINE") != "1":
        pytest.skip("Explicit LIVESPEC_REAL_PIPELINE=1 required for the full production workflow")
    runtime = os.environ.get("LIVESPEC_WITNESS_RUNTIME", "codex")
    result = run_pipeline_trial(runtime, report_path=tmp_path / "pipeline-trial.json")
    assert result.stage == "spec_feature_pipeline"
    assert result.outcome == "first_attempt_success", result.to_dict()
    assert result.evaluation and result.evaluation.behavior_passed
