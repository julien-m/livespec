# @spec(AC-001)
# @spec(AC-002)
# @spec(AC-003)
# @spec(AC-004)
# @spec(AC-005)
# @spec(AC-006)
# @spec(AC-007)
# @spec(FR-006)

"""Static contract tests for the informative-only Design direction carry."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _text(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def test_spec_template_carries_optional_design_direction() -> None:
    text = _text("system/templates/spec-template.md")
    assert "**Design direction:**" in text
    assert "Omit the line entirely when no direction exists" in text
    assert "never a validation criterion" in text


def test_spec_specify_populates_design_direction_with_precedence() -> None:
    text = _text(".agent-sync/skills/spec-specify/SKILL.md")
    assert "Carry design direction" in text
    assert "penflow/design-read.json" in text
    assert ".specs/design/theme.md" in text
    assert "default-direction" in text
    assert "MUST NOT be used to pass/fail" in text
    assert "Never emit a placeholder" in text


def test_spec_init_wizard_and_import_carry_direction() -> None:
    text = _text(".agent-sync/skills/spec-init/SKILL.md")
    assert "default-direction" in text
    assert "Design direction extraction" in text
    assert "## Design direction" in text


def test_design_direction_never_leaks_into_judgement_commands() -> None:
    for command in ("spec-check", "spec-test"):
        text = _text(f".agent-sync/skills/{command}/SKILL.md")
        assert "Design direction" not in text


def test_spec_system_documents_carry_as_informative() -> None:
    text = _text(".specs/spec-system.md")
    assert "**Design direction:**" in text
    assert "never an input to fidelity checks" in text


def test_screens_parser_ignores_design_direction_line(tmp_path: Path) -> None:
    from validator.cli_commands.ui_runner_cmd import _discover_screens_in_feature

    feature_dir = tmp_path / "999-sample"
    feature_dir.mkdir()
    (feature_dir / "spec.md").write_text(
        "# Feature Spec: Sample\n\n"
        "## Screens\n\n"
        "**Design direction:** Calm, editorial SaaS - low motion.\n\n"
        "| Screen | Status | Reference |\n"
        "|--------|--------|-----------|\n"
        "| dashboard | New | [dashboard.png](../../design/screens/dashboard.png) |\n"
        "| settings | Modified | [settings.png](../../design/screens/settings.png) |\n",
        encoding="utf-8",
    )
    assert _discover_screens_in_feature(feature_dir) == ["dashboard", "settings"]
