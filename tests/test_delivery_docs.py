"""Skills, hook and protocol follow the lane and review once (feature 086 AC-008)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


# @spec AC-008: No review per step, one final review
#   — .specs/features/086-risk-proportional-delivery/spec.md#ac-008
def test_step_hook_dispatches_no_review() -> None:
    hook = _read("system/hooks/after-implement-step.md")
    assert "Dispatch no reviewer and no audit for a step" in hook
    assert "delivery-review.md" in hook
    assert "At most two correction iterations" not in hook


def test_protocol_forbids_audit_skill_and_codex() -> None:
    protocol = _read("system/delivery-review.md")
    for text in (
        "Do not invoke the retired `audit` skill, Codex",
        "effort `high`",
        "livespec delivery review prepare",
        "livespec delivery review record",
        "livespec delivery review verify",
        "round_cap_reached",
    ):
        assert text in protocol


def test_implement_skill_runs_checks_per_step_and_one_review() -> None:
    skill = _read(".agent-sync/skills/spec-implement/SKILL.md")
    assert "STEP 0.95 — Delivery lane" in skill
    assert "Phase 6.8 — Delivery review (once per feature)" in skill
    assert "Spin up a **Spec Reviewer** subagent" not in skill
    assert "Spin up a **Code Quality Reviewer** subagent" not in skill
    assert "after tests and both step reviewers pass" not in skill
    assert "[lane-light]" in skill and "[lane-full]" in skill


def test_feature_and_ship_skills_reuse_the_single_review() -> None:
    feature = _read(".agent-sync/skills/spec-feature/SKILL.md")
    assert "livespec delivery review verify --feature NNN-feature-name" in feature
    ship = _read(".agent-sync/skills/spec-ship/SKILL.md")
    assert "audit failed after 3 attempts" not in ship
    assert "round_cap_reached" in ship


def test_both_spec_system_copies_describe_the_lanes() -> None:
    for relative in ("system/spec-system.md", ".specs/spec-system.md"):
        text = _read(relative)
        assert "### Delivery lanes (risk-proportional implementation)" in text
        assert "livespec delivery lane --feature <slug>" in text
