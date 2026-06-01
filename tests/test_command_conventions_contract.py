"""Contract tests for convention propagation in LiveSpec command skills."""

from __future__ import annotations

from pathlib import Path

SKILLS_DIR = Path(__file__).resolve().parents[1] / ".agent-sync" / "skills"
UI_DOMAINS = ("design-tokens", "design-components", "design-views", "design-quality")


def _skill_text(command: str) -> str:
    return (SKILLS_DIR / command / "SKILL.md").read_text(encoding="utf-8")


def test_spec_check_loads_and_reports_convention_compliance() -> None:
    text = _skill_text("spec-check")

    assert ".conventions/index.md" in text
    assert "Convention Compliance" in text
    assert "convention gap" in text
    assert "ai-ressources" in text
    assert "`code`" in text
    for domain in UI_DOMAINS:
        assert f"`{domain}`" in text


def test_spec_fix_builds_explicit_conventions_payload() -> None:
    text = _skill_text("spec-fix")

    assert "Conventions payload" in text
    assert "always include `code`" in text
    assert "missing-ui-domains" in text
    assert "livespec conventions refresh --repo . --full" in text
    for domain in UI_DOMAINS:
        assert f"`{domain}`" in text


def test_spec_implement_refreshes_missing_conventions_before_payload() -> None:
    text = _skill_text("spec-implement")

    assert "livespec conventions refresh --repo . --full" in text
    assert "Set to `NONE` only if refresh fails" in text
    assert "missing-ui-domains" in text
