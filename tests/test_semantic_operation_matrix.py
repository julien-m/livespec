"""Native validation operations never discard another requested action or modifier."""

import json
from itertools import combinations
from pathlib import Path

import pytest
from typer.testing import CliRunner

from tests.review_support import reviewed_project
from validator.clarify_gate import scan_clarification_opportunities
from validator.cli import app

OPERATIONS = (
    ("--clarify",),
    ("--clarification-answer", "answer.json"),
    ("--prepare-review", "plan"),
    ("--ingest-review", "review.json"),
    ("--progression", "plan"),
)
PAIRS = tuple(pair for pair in combinations(OPERATIONS, 2) if pair != OPERATIONS[:2])
LEGACY_OPTIONS = (
    ("--staged",),
    ("--state-files",),
    ("--pre-impl",),
    ("--sdk-isolated",),
    ("--review-spec",),
    ("--plan-review",),
    ("--contradiction-only",),
    ("--reindex",),
    ("--mutate",),
    ("--experimental-multi-model",),
    ("--list-excluded",),
    ("--fix",),
    ("--smart",),
    ("--auto",),
    ("--dry-run",),
    ("--warn-only",),
    ("--score-only",),
    ("--coherence",),
    ("--coherence-only",),
    ("--rules", "R1"),
    ("--wave", "1"),
    ("--ignore", "R1"),
    ("--strict",),
    ("--no-suppress",),
    ("--semantic",),
    ("--scorecard",),
    ("--all-reviewers",),
    ("--no-review",),
    ("--migrate",),
    ("--format", "full"),
    ("--format", "json"),
)


@pytest.mark.parametrize("pair", PAIRS)
def test_every_distinct_semantic_operation_pair_rejects_without_writes(
    tmp_path: Path, pair: tuple[tuple[str, ...], tuple[str, ...]]
) -> None:
    feature = reviewed_project(tmp_path)
    before = {str(p): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    result = CliRunner().invoke(app, ["validate", str(feature), *pair[0], *pair[1]])
    assert result.exit_code == 1
    assert result.output.startswith("Error:")
    assert {str(p): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()} == before


@pytest.mark.parametrize("operation", OPERATIONS)
@pytest.mark.parametrize("modifier", LEGACY_OPTIONS)
def test_semantic_operation_rejects_unconsumed_legacy_options_before_resolution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    operation: tuple[str, ...],
    modifier: tuple[str, ...],
) -> None:
    calls: list[Path | None] = []

    def resolve(path: Path | None) -> Path:
        calls.append(path)
        raise AssertionError("Rejected modes cannot resolve project inputs")

    monkeypatch.setattr("validator.cli._require_specs_root", resolve)
    result = CliRunner().invoke(app, ["validate", str(tmp_path), *operation, *modifier])
    assert result.exit_code == 1
    assert result.output.startswith("Error:")
    assert calls == []


@pytest.mark.parametrize("operation", (OPERATIONS[0], OPERATIONS[2], OPERATIONS[4]))
def test_review_kind_cannot_be_silently_ignored_outside_ingest(
    tmp_path: Path, operation: tuple[str, ...]
) -> None:
    feature = reviewed_project(tmp_path)
    result = CliRunner().invoke(
        app, ["validate", str(feature), *operation, "--review-kind", "spec"]
    )
    assert result.exit_code == 1
    assert "--review-kind requires --ingest-review" in result.output


def test_clarify_with_answer_is_one_explicit_source_bound_operation(tmp_path: Path) -> None:
    feature = reviewed_project(tmp_path)
    spec = feature / "spec.md"
    spec.write_text(spec.read_text() + "\n## FR-002\nExport must be secure.\n")
    item = scan_clarification_opportunities(spec)[0]
    answer = tmp_path / "answer.json"
    answer.write_text(
        json.dumps(
            {
                "requirement_id": item.requirement_id,
                "decision_key": item.decision_key,
                "source_hash": item.source_hash,
                "answer": "Use TLS 1.3 for exports.",
            }
        )
    )
    result = CliRunner().invoke(
        app, ["validate", str(feature), "--clarify", "--clarification-answer", str(answer)]
    )
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["dependent_review"] == "stale"
    assert "Use TLS 1.3 for exports." in spec.read_text()


def test_native_prepare_preserves_explicit_model_and_budget(tmp_path: Path) -> None:
    feature = reviewed_project(tmp_path)
    result = CliRunner().invoke(
        app,
        [
            "validate",
            str(feature),
            "--prepare-review",
            "plan",
            "--model",
            "reviewer/v1",
            "--review-max-chars",
            "60000",
        ],
    )
    assert result.exit_code == 0, result.output
    prepared = json.loads(result.output)["prepared"]
    assert prepared["reviewer_model"] == "reviewer/v1"
    assert prepared["max_chars"] == 60000


@pytest.mark.parametrize("option", ("--prepare-review", "--progression"))
def test_present_empty_operation_cannot_fall_back_to_legacy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, option: str
) -> None:
    calls: list[Path | None] = []

    def resolve(path: Path | None) -> Path:
        calls.append(path)
        raise AssertionError("Empty operation reached project resolution")

    monkeypatch.setattr("validator.cli._require_specs_root", resolve)
    result = CliRunner().invoke(app, ["validate", str(tmp_path), option, ""])
    assert result.exit_code == 1
    assert result.output.startswith("Error:")
    assert calls == []
