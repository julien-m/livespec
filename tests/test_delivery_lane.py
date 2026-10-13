"""Delivery lane from the reviewed QE classification (feature 086 AC-001, AC-002)."""

# @spec AC-001: Light lane
#   — .specs/features/086-risk-proportional-delivery/spec.md#ac-001
# @spec AC-002: Full lane reasons
#   — .specs/features/086-risk-proportional-delivery/spec.md#ac-002

from __future__ import annotations

from pathlib import Path

import pytest

from tests.delivery_support import FEATURE, MODEL, make_project, spec_text
from validator.delivery.lane import classify


def _codes(spec: str) -> list[str]:
    return [reason.code for reason in classify(FEATURE, spec).reasons]


# @spec AC-001: Light lane
#   — .specs/features/086-risk-proportional-delivery/spec.md#ac-001
def test_medium_shared_with_current_review_is_light(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = make_project(tmp_path)
    project.review_spec()
    monkeypatch.chdir(project.root)
    code, payload = project.json("delivery", "lane", "--feature", FEATURE, "--model", MODEL)
    assert (code, payload["lane"], payload["reasons"]) == (0, "light", [])
    assert (payload["criticality"], payload["blast_radius"]) == ("medium", "shared")


@pytest.mark.parametrize(
    "qe",
    [
        "| Field | Classification |\n|---|---|\n| Criticality | Low |\n| Blast radius | Local |",
        "- **Criticality:** Low\n- **Blast radius:** Shared",
        "- **Risk:** low criticality; local blast radius.",
    ],
)
def test_every_existing_classification_form_is_parsed(qe: str) -> None:
    assert _codes(spec_text(qe)) == []


@pytest.mark.parametrize(
    ("qe", "expected"),
    [
        (None, ["qe_section_missing"]),
        ("- **Risk:** primary risk Contract.", ["criticality_missing", "blast_radius_missing"]),
        ("- **Risk:** High criticality; Local blast radius.", ["criticality_high"]),
        ("- **Risk:** Low criticality; Cross-system blast radius.", ["blast_radius_wide"]),
        ("- **Risk:** Low criticality; External blast radius.", ["blast_radius_wide"]),
        (
            "- **Risk:** Low criticality; Local blast radius.\n- **Criticality:** High",
            ["qe_classification_conflicting"],
        ),
        (
            "- **Risk:** Low criticality; Local blast radius.\n- **Delivery lane:** full",
            ["declared_full"],
        ),
    ],
)
def test_full_lane_reasons(qe: str | None, expected: list[str]) -> None:
    assert _codes(spec_text(qe)) == expected


def test_light_declaration_cannot_override_high_risk() -> None:
    spec = spec_text(
        "- **Risk:** High criticality; Local blast radius.\n- **Delivery lane:** light"
    )
    assert classify(FEATURE, spec).lane == "full"


def test_qe_section_ends_at_next_heading() -> None:
    spec = spec_text("- **Risk:** Low criticality; Local blast radius.") + (
        "\n## Notes\n\nHigh criticality elsewhere is not the QE classification.\n"
    )
    assert _codes(spec) == []


def test_missing_or_stale_review_keeps_the_full_lane(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = make_project(tmp_path)
    monkeypatch.chdir(project.root)
    _, payload = project.json("delivery", "lane", "--feature", FEATURE, "--model", MODEL)
    assert [r["code"] for r in payload["reasons"]] == ["spec_review_not_current"]  # type: ignore[index]
    project.review_spec()
    # A downgrade after review changes the normative spec, so the receipt is stale.
    project.write(
        f".specs/features/{FEATURE}/spec.md",
        spec_text("- **Risk:** Low criticality; Local blast radius."),
    )
    _, payload = project.json("delivery", "lane", "--feature", FEATURE, "--model", MODEL)
    assert payload["lane"] == "full"
    _, payload = project.json("delivery", "lane", "--feature", FEATURE, "--model", "other-model")
    assert payload["lane"] == "full"


def test_unknown_feature_exits_2(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project = make_project(tmp_path)
    monkeypatch.chdir(project.root)
    assert project.run("delivery", "lane", "--feature", "999-none").exit_code == 2
