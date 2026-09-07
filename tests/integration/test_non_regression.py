"""Two opt-in workflow runs check immediate repeatability without statistical confidence."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from tests.integration.helpers.witness_pipeline import run_pipeline_trial


@pytest.mark.level_3c
@pytest.mark.slow
def test_pipeline_behavior_stable_across_bounded_repetitions(tmp_path: Path) -> None:
    if os.environ.get("LIVESPEC_REPEAT_PIPELINE") != "1":
        pytest.skip("Explicit LIVESPEC_REPEAT_PIPELINE=1 required for two full pipeline runs")
    runtime = os.environ.get("LIVESPEC_WITNESS_RUNTIME", "codex")
    # Two runs add one repeat to a single smoke while limiting paid model invocations;
    # both must pass, but this small sample cannot estimate a reliability rate.
    results = [
        run_pipeline_trial(runtime, report_path=tmp_path / f"pipeline-{attempt}.json")
        for attempt in range(2)
    ]
    assert all(result.outcome == "first_attempt_success" for result in results), [
        result.to_dict() for result in results
    ]
