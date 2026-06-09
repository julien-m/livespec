# LiveSpec traceability anchors
# @spec(AC-012)
# @spec(AC-013)
# @spec(AC-017)
# @spec(AC-029)
# @spec(AC-030)
# @spec(AC-045)

"""Static documentation and skill tests for User Journeys v2."""

from __future__ import annotations

from pathlib import Path


def test_spec_journey_skill_documents_create_bootstrap_and_compiled_run() -> None:
    """FR-041: `$spec-journey` exposes creation, bootstrap, impact, and run workflows."""
    skill = Path(".agent-sync/skills/spec-journey/SKILL.md")

    content = skill.read_text(encoding="utf-8")

    assert "$spec-journey create" in content
    assert "$spec-journey bootstrap --from-existing" in content
    assert "implemented features" in content
    assert "compile once" in content
    assert "livespec journey run" in content


def test_user_journeys_doc_describes_v2_global_layout() -> None:
    """FR-041: user journey system docs describe the v2 canonical layout."""
    content = Path("system/testing/user-journeys.md").read_text(encoding="utf-8")

    assert ".specs/journeys/<journey-id>/journey.yaml" in content
    assert "livespec journey run" in content
    assert "does not compile" in content
