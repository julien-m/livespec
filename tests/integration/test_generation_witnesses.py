# @spec(AC-011)
# .specs/features/078-requirement-evidence-integrity/spec.md#ac-011
"""Behavioral witness sensitivity, isolation and explicitly opt-in real trials."""

from __future__ import annotations

import os
import shutil
from dataclasses import replace
from pathlib import Path

import pytest

from tests.integration.helpers.witness_evaluator import (
    FIXTURES,
    WITNESSES,
    evaluate_candidate,
    freeze_oracle,
)
from tests.integration.helpers.witness_generation import run_generation_trial


def seed_candidate(root: Path, witness: str) -> Path:
    candidate = root / witness
    shutil.copytree(FIXTURES / f"witness-{witness}" / "seed", candidate)
    return candidate


@pytest.mark.level_3a
@pytest.mark.parametrize("witness", WITNESSES)
def test_correct_seed_observes_real_behavior(tmp_path: Path, witness: str) -> None:
    result = evaluate_candidate(freeze_oracle(witness), seed_candidate(tmp_path, witness))
    assert result.behavior_passed, result
    assert result.assertions > 0
    if witness == "ui-form":
        assert result.status == "blocked"
        assert result.reason == "independent_build_manifest_required"
    else:
        assert result.status == "pass"


@pytest.mark.level_3a
@pytest.mark.parametrize(
    ("witness", "filename", "original", "mutation"),
    [
        ("python-purge", "purge.py", "path.unlink()", "pass"),
        ("python-purge", "purge.py", ">= 86400", ">= 0"),
        ("typescript-api", "app.ts", '!== "Bearer witness"', '=== "never"'),
        ("typescript-api", "app.ts", "writeFileSync(storePath, JSON.stringify(stored));", ""),
        ("ui-form", "index.html", " required", ""),
        ("ui-form", "index.html", "success.hidden = false;", "success.hidden = true;"),
    ],
)
def test_behavioral_mutants_fail(
    tmp_path: Path, witness: str, filename: str, original: str, mutation: str
) -> None:
    candidate = seed_candidate(tmp_path, witness)
    source = candidate / filename
    text = source.read_text()
    assert original in text
    source.write_text(text.replace(original, mutation))
    result = evaluate_candidate(freeze_oracle(witness), candidate)
    assert result.status == "failure", result
    assert not result.behavior_passed


@pytest.mark.level_3a
@pytest.mark.parametrize("escape", ("oracle", "symlink"))
def test_modified_oracle_or_candidate_escape_invalidates(tmp_path: Path, escape: str) -> None:
    oracle = freeze_oracle("python-purge")
    candidate = seed_candidate(tmp_path, "python-purge")
    if escape == "oracle":
        oracle = replace(oracle, sha256="changed")
    else:
        (candidate / "outside").symlink_to(tmp_path)
    assert evaluate_candidate(oracle, candidate).status == "invalid"


@pytest.mark.level_3c
@pytest.mark.parametrize("witness", WITNESSES)
def test_real_native_generation(witness: str, tmp_path: Path) -> None:
    if os.environ.get("LIVESPEC_REAL_WITNESSES") != "1":
        pytest.skip("Explicit LIVESPEC_REAL_WITNESSES=1 required for model calls")
    runtime = os.environ.get("LIVESPEC_WITNESS_RUNTIME", "claude")
    selected = os.environ.get("LIVESPEC_WITNESSES", ",".join(WITNESSES)).split(",")
    if witness not in selected:
        pytest.skip("Witness outside declared selection")
    result = run_generation_trial(
        witness, runtime, report_path=tmp_path / f"{runtime}-{witness}.json"
    )
    assert result.outcome in ("first_attempt_success", "repaired_success"), result.to_dict()


@pytest.mark.level_3a
def test_candidate_cannot_exit_oracle_with_forged_stdout(tmp_path: Path) -> None:
    candidate = seed_candidate(tmp_path, "typescript-api")
    (candidate / "app.ts").write_text(
        "console.log(JSON.stringify({passed:true, assertions:6})); process.exit(0);"
    )
    result = evaluate_candidate(freeze_oracle("typescript-api"), candidate)
    assert result.status == "failure"
    assert not result.behavior_passed
