"""The reviewer model and budget come from options, else the configuration (feature 093)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest
from typer.testing import CliRunner

from tests.review_support import reviewed_project
from tests.stable_review_support import FEATURE, make_root
from validator.cli import app
from validator.progression_gate import ProgressionBlocked, require_progression
from validator.semantic.review_identity_config import (
    ReviewIdentity,
    ReviewIdentityError,
    resolve_review_identity,
)

CONFIG = ".specs/semantic/config.yaml"


def _config(root: Path, text: str | None) -> None:
    path = root / CONFIG
    if text is None:
        path.unlink(missing_ok=True)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def _invoke(root: Path, monkeypatch: pytest.MonkeyPatch, *args: str) -> tuple[int, str]:
    monkeypatch.chdir(root)
    result = CliRunner().invoke(app, list(args))
    return result.exit_code, result.output


# @spec AC-001: Option, then configuration, else review_model_required
#   — .specs/features/093-configured-review-identity/spec.md#ac-001
def test_options_win_over_the_configuration(tmp_path: Path) -> None:
    _config(tmp_path, "review_model: m1\nreview_max_chars: 70000\n")
    explicit = resolve_review_identity(tmp_path, "m2", 50000)
    assert explicit == ReviewIdentity("m2", 50000, "option")
    assert resolve_review_identity(tmp_path) == ReviewIdentity("m1", 70000, "configuration")


def test_defaults_and_the_reviewer_list(tmp_path: Path) -> None:
    _config(tmp_path, "review_reviewers: [r1, r2]\n")
    assert resolve_review_identity(tmp_path) == ReviewIdentity("r1", 60000, "configuration")


@pytest.mark.parametrize(
    "config",
    [None, "review_max_chars: 70000\n", "review_model: ''\n", "review_model: 7\n"],
)
def test_no_named_model_is_required(tmp_path: Path, config: str | None) -> None:
    _config(tmp_path, config)
    with pytest.raises(ReviewIdentityError, match="review_model_required") as error:
        resolve_review_identity(tmp_path)
    assert error.value.code == "review_model_required"


@pytest.mark.parametrize("model", ["default", "unknown"])
def test_placeholder_models_name_no_reviewer(tmp_path: Path, model: str) -> None:
    with pytest.raises(ReviewIdentityError, match="review_model_required"):
        resolve_review_identity(tmp_path, model)


@pytest.mark.parametrize("budget", ["999", "200001", "'abc'", "true", "60000.5"])
def test_configured_budget_out_of_bounds_is_refused(tmp_path: Path, budget: str) -> None:
    _config(tmp_path, f"review_model: m1\nreview_max_chars: {budget}\n")
    with pytest.raises(ReviewIdentityError, match="review_max_chars_out_of_bounds"):
        resolve_review_identity(tmp_path)


@pytest.mark.parametrize("budget", [999, 200001])
def test_explicit_budget_out_of_bounds_is_refused(tmp_path: Path, budget: int) -> None:
    with pytest.raises(ReviewIdentityError, match="review_max_chars_out_of_bounds"):
        resolve_review_identity(tmp_path, "m1", budget)


def test_bounds_are_inclusive(tmp_path: Path) -> None:
    assert resolve_review_identity(tmp_path, "m1", 1000).max_chars == 1000
    assert resolve_review_identity(tmp_path, "m1", 200000).max_chars == 200000


def _plan_goal(root: Path, monkeypatch: pytest.MonkeyPatch, *flags: str) -> tuple[int, str]:
    args = ["goal", "render", "spec-plan", "--feature", "001-test", "--json"]
    return _invoke(root, monkeypatch, *args, *(["--flags", " ".join(flags)] if flags else []))


def _reviewer_models(output: str) -> set[str]:
    tasks = cast(list[dict[str, Any]], json.loads(output)["canonical"]["tasks"])
    return {
        str(task["expected_evidence"]["reviewer_model"])
        for task in tasks
        if task.get("evidence_kind") == "review"
    }


def test_goal_render_without_model_expects_the_configured_reviewer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    reviewed_project(tmp_path)
    _config(tmp_path, "review_model: m1\n")
    code, output = _plan_goal(tmp_path, monkeypatch)
    assert code == 0, output
    assert _reviewer_models(output) == {"m1"}
    code, output = _plan_goal(tmp_path, monkeypatch, "--model=m2")
    assert code == 0, output
    assert _reviewer_models(output) == {"m2"}


@pytest.mark.parametrize(
    ("config", "error"),
    [
        (None, "review_model_required"),
        ("review_model: m1\nreview_max_chars: 500\n", "review_max_chars_out_of_bounds"),
    ],
)
def test_goal_render_refuses_an_unresolved_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, config: str | None, error: str
) -> None:
    reviewed_project(tmp_path)
    _config(tmp_path, config)
    code, output = _plan_goal(tmp_path, monkeypatch)
    assert (code, error in output, "contract-file:" in output) == (2, True, False)


def test_progression_reads_the_configured_model(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = make_root(tmp_path)
    feature_dir = f".specs/features/{FEATURE}"
    code, output = _invoke(root, monkeypatch, "validate", feature_dir, "--progression", "implement")
    assert (code, "Progression: READY" in output) == (0, True), output
    _config(root, None)
    code, output = _invoke(root, monkeypatch, "validate", feature_dir, "--progression", "implement")
    assert (code, "review_model_required" in output) == (1, True), output


def test_progression_refuses_a_configured_budget_out_of_bounds(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    _config(root, "review_model: reviewer/v1\nreview_max_chars: 250000\n")
    with pytest.raises(ProgressionBlocked, match="review_max_chars_out_of_bounds"):
        require_progression(root, FEATURE, "implement")


def test_delivery_lane_reads_the_configuration_or_requires_a_model(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = make_root(tmp_path)
    lane = ("delivery", "lane", "--feature", FEATURE, "--json")
    for args in (lane, (*lane, "--model", "reviewer/v1")):
        code, output = _invoke(root, monkeypatch, *args)
        assert (code, json.loads(output)["lane"]) == (0, "light"), output
    # The configuration is a review dependency: removing it is the last step.
    _config(root, None)
    code, output = _invoke(root, monkeypatch, *lane)
    # Replaces the 086 behavior (exit 0, full lane, spec_review_not_current) for this case.
    assert (code, "review_model_required" in output, "lane" in output) == (2, True, False)


def test_delivery_lane_refuses_a_budget_out_of_bounds(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = make_root(tmp_path)
    lane = ("delivery", "lane", "--feature", FEATURE, "--review-max-chars", "999")
    code, output = _invoke(root, monkeypatch, *lane)
    assert (code, "review_max_chars_out_of_bounds" in output) == (2, True)


def test_revision_open_requires_a_model(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = make_root(tmp_path)
    _config(root, None)
    args = ("delivery", "revision", "open", "--feature", FEATURE, "--json")
    code, output = _invoke(root, monkeypatch, *args)
    assert (code, json.loads(output)["error"]) == (1, "review_model_required")


@pytest.mark.parametrize("model", ["", "m1"])
@pytest.mark.parametrize("broken", ["review_model: [unclosed\n", b"review_model: \xff\n", None])
def test_unreadable_configuration_is_refused(
    tmp_path: Path, model: str, broken: str | bytes | None
) -> None:
    path = tmp_path / CONFIG
    path.parent.mkdir(parents=True)
    if broken is None:
        path.mkdir()  # a directory where the file belongs
    elif isinstance(broken, bytes):
        path.write_bytes(broken)
    else:
        path.write_text(broken)
    with pytest.raises(ReviewIdentityError, match="review_config_invalid"):
        resolve_review_identity(tmp_path, model)


@pytest.mark.parametrize(
    ("config", "model", "expected"),
    [
        ("review_model: ' '\n", "", None),
        ("review_model: m1\n", " ", None),
        ("review_model: m1\n", " m2 ", "m2"),
        ("review_reviewers: [default, ' ', real/m]\n", "", "real/m"),
        ("review_reviewers: real/m\n", "", None),
        ("- review_model: m1\n", "", None),
    ],
)
def test_only_a_named_model_resolves(
    tmp_path: Path, config: str, model: str, expected: str | None
) -> None:
    _config(tmp_path, config)
    if expected is None:
        with pytest.raises(ReviewIdentityError, match="review_model_required"):
            resolve_review_identity(tmp_path, model)
    else:
        assert resolve_review_identity(tmp_path, model).model == expected


def test_budget_errors_stay_short(tmp_path: Path) -> None:
    _config(tmp_path, f"review_model: m1\nreview_max_chars: {'9' * 400}\n")
    with pytest.raises(ReviewIdentityError) as error:
        resolve_review_identity(tmp_path)
    assert len(str(error.value)) < 200


def test_commands_refuse_an_unreadable_configuration_with_model(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = make_root(tmp_path)
    _config(root, "review_model: [unclosed\n")
    lane = ("delivery", "lane", "--feature", FEATURE, "--model", "reviewer/v1", "--json")
    assert _invoke(root, monkeypatch, *lane)[0] == 2
    goal = ("goal", "render", "spec-plan", "--feature", FEATURE, "--flags", "--model=reviewer/v1")
    code, output = _invoke(root, monkeypatch, *goal)
    assert (code, "review_config_invalid" in output) == (2, True), output
    progression = ("validate", f".specs/features/{FEATURE}", "--progression", "implement")
    code, output = _invoke(root, monkeypatch, *progression, "--model", "reviewer/v1")
    assert (code, "review_config_invalid" in output) == (1, True), output


def test_goal_render_refuses_a_malformed_budget_flag(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = make_root(tmp_path)
    goal = ("goal", "render", "spec-plan", "--feature", FEATURE, "--flags")
    code, output = _invoke(root, monkeypatch, *goal, "--review-max-chars=²")
    assert (code, "review_max_chars_out_of_bounds" in output) == (2, True), output


@pytest.mark.parametrize(
    ("config", "flags", "code"),
    [
        (None, [], "review_model_required"),
        ("review_model: reviewer/v1\n", ["--review-max-chars=²"], "review_max_chars_out_of_bounds"),
    ],
)
def test_implement_goal_lane_stays_full_without_an_identity(
    tmp_path: Path, config: str | None, flags: list[str], code: str
) -> None:
    from validator.delivery.goal import goal_delivery_lane

    root = make_root(tmp_path)
    _config(root, config)
    decision = goal_delivery_lane("spec-implement", root, FEATURE, flags)
    assert decision is not None
    reasons = cast(list[dict[str, str]], decision["reasons"])
    assert (decision["lane"], [r["code"] for r in reasons]) == ("full", [code])


def test_delivery_review_verify_requires_a_model(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = make_root(tmp_path)
    _config(root, None)
    verify = ("delivery", "review", "verify", "--feature", FEATURE, "--json")
    code, output = _invoke(root, monkeypatch, *verify)
    assert (code, "review_model_required" in output) == (2, True), output
