# LiveSpec traceability anchors
# @spec(AC-004)
# @spec(AC-008)
# @spec(FR-010)

"""Tests for validator.integrations (Level 0 user integration discovery)."""

from __future__ import annotations

from pathlib import Path

import pytest

from validator.integrations import (
    Integration,
    _reset_warnings_for_tests,
    discover_integrations,
    resolve_for,
    valid_command_names,
)


@pytest.fixture(autouse=True)
def _clear_warning_dedup() -> None:
    _reset_warnings_for_tests()


# ---------------------------------------------------------------------------
# Canonical command registry
# ---------------------------------------------------------------------------


def test_command_registry_excludes_expectations() -> None:
    names = valid_command_names()
    assert "spec-plan" in names
    assert "spec-feature" in names
    assert "spec-plan.expectations" not in names
    assert "spec-feature.expectations" not in names
    assert not any(n.endswith(".expectations") for n in names)


def test_integration_commands_accept_slash_aliases(tmp_path: Path) -> None:
    _write(
        tmp_path / "alias.md",
        "---\nintegration: alias\ncommands: [/spec-plan, /spec-check]\n---\nbody\n",
    )

    integrations = discover_integrations(integrations_dir=tmp_path)

    assert len(integrations) == 1
    assert integrations[0].commands == ("spec-plan", "spec-check")


# ---------------------------------------------------------------------------
# Absence-tolerance (C.fix-3)
# ---------------------------------------------------------------------------


def test_absent_directory_returns_empty(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    missing = tmp_path / "does-not-exist"
    assert discover_integrations(integrations_dir=missing) == []
    captured = capsys.readouterr()
    assert captured.err == ""


def test_empty_directory_returns_empty(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    assert discover_integrations(integrations_dir=empty) == []
    captured = capsys.readouterr()
    assert captured.err == ""


# ---------------------------------------------------------------------------
# Engagement test — silent ignore for non-engaged files
# ---------------------------------------------------------------------------


def _write(p: Path, content: str) -> None:
    p.write_text(content, encoding="utf-8")


def test_file_without_frontmatter_silently_ignored(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    d = tmp_path / "cfg"
    d.mkdir()
    _write(d / "notes.md", "# Just my notes\n\nNothing structured here.\n")
    assert discover_integrations(integrations_dir=d) == []
    assert capsys.readouterr().err == ""


def test_file_missing_integration_key_silently_ignored(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    d = tmp_path / "cfg"
    d.mkdir()
    _write(
        d / "x.md",
        "---\ncommands: [plan]\n---\n\nbody\n",
    )
    assert discover_integrations(integrations_dir=d) == []
    assert capsys.readouterr().err == ""


def test_file_missing_commands_key_silently_ignored(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    d = tmp_path / "cfg"
    d.mkdir()
    _write(
        d / "x.md",
        "---\nintegration: foo\n---\n\nbody\n",
    )
    assert discover_integrations(integrations_dir=d) == []
    assert capsys.readouterr().err == ""


# ---------------------------------------------------------------------------
# Engaged & well-formed → returned
# ---------------------------------------------------------------------------


def test_engaged_well_formed_targets_plan(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    d = tmp_path / "cfg"
    d.mkdir()
    _write(
        d / "mockups.md",
        "---\n"
        "integration: mockups\n"
        "commands: [specify, plan]\n"
        "phase: before\n"
        "mode: extend\n"
        "order: 50\n"
        "---\n"
        "\n"
        "Inject mockups before plan.\n",
    )
    matches = resolve_for("before", "plan", integrations_dir=d)
    assert len(matches) == 1
    assert matches[0].name == "mockups"
    assert "Inject mockups before plan." in matches[0].body
    assert capsys.readouterr().err == ""


def test_scope_isolation_other_command_not_targeted(tmp_path: Path) -> None:
    d = tmp_path / "cfg"
    d.mkdir()
    _write(
        d / "mockups.md",
        "---\nintegration: mockups\ncommands: [plan]\n---\nbody\n",
    )
    assert resolve_for("before", "implement", integrations_dir=d) == []


# ---------------------------------------------------------------------------
# Engaged but malformed → 1 stderr warning + skipped
# ---------------------------------------------------------------------------


def test_unknown_command_emits_single_warning(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    d = tmp_path / "cfg"
    d.mkdir()
    _write(
        d / "x.md",
        "---\nintegration: x\ncommands: [bogus]\n---\nbody\n",
    )
    result = discover_integrations(integrations_dir=d)
    assert result == []
    err = capsys.readouterr().err
    assert err.count("⚠ ") == 1
    assert 'unknown command "spec-bogus"' in err


def test_invalid_mode_is_skipped_with_warning(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    d = tmp_path / "cfg"
    d.mkdir()
    _write(
        d / "x.md",
        "---\nintegration: x\ncommands: [plan]\nmode: merge\n---\nbody\n",
    )
    result = discover_integrations(integrations_dir=d)
    assert result == []
    err = capsys.readouterr().err
    assert err.count("⚠ ") == 1
    assert "invalid mode" in err and "merge" in err


def test_broken_yaml_emits_single_warning(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    d = tmp_path / "cfg"
    d.mkdir()
    _write(
        d / "x.md",
        "---\nintegration: [unclosed\n---\nbody\n",
    )
    result = discover_integrations(integrations_dir=d)
    assert result == []
    err = capsys.readouterr().err
    # YAML errors are multi-line by nature — verify ONE warning emitted
    # (single "⚠ <path>:" prefix), not zero, not duplicated.
    assert err.count("⚠ ") == 1
    assert "broken frontmatter" in err


# ---------------------------------------------------------------------------
# Ordering and override
# ---------------------------------------------------------------------------


def test_ordering_by_order_then_basename(tmp_path: Path) -> None:
    d = tmp_path / "cfg"
    d.mkdir()
    _write(d / "b.md", "---\nintegration: b\ncommands: [plan]\norder: 10\n---\nB\n")
    _write(d / "a.md", "---\nintegration: a\ncommands: [plan]\norder: 20\n---\nA\n")
    _write(d / "c.md", "---\nintegration: c\ncommands: [plan]\norder: 20\n---\nC\n")
    result = resolve_for("before", "plan", integrations_dir=d)
    assert [i.name for i in result] == ["b", "a", "c"]


def test_override_replaces_other_l0(tmp_path: Path) -> None:
    d = tmp_path / "cfg"
    d.mkdir()
    _write(d / "a.md", "---\nintegration: a\ncommands: [plan]\n---\nA\n")
    _write(
        d / "b.md",
        "---\nintegration: b\ncommands: [plan]\nmode: override\n---\nB\n",
    )
    result = resolve_for("before", "plan", integrations_dir=d)
    assert len(result) == 1
    assert result[0].name == "b"


def test_multiple_overrides_raise(tmp_path: Path) -> None:
    d = tmp_path / "cfg"
    d.mkdir()
    _write(
        d / "a.md",
        "---\nintegration: a\ncommands: [plan]\nmode: override\n---\nA\n",
    )
    _write(
        d / "b.md",
        "---\nintegration: b\ncommands: [plan]\nmode: override\n---\nB\n",
    )
    with pytest.raises(ValueError, match="Multiple override integrations"):
        resolve_for("before", "plan", integrations_dir=d)


def test_dedup_same_name_same_phase_same_commands_raises(tmp_path: Path) -> None:
    d = tmp_path / "cfg"
    d.mkdir()
    _write(d / "a.md", "---\nintegration: dup\ncommands: [plan]\n---\nA\n")
    _write(d / "b.md", "---\nintegration: dup\ncommands: [plan]\n---\nB\n")
    with pytest.raises(ValueError, match="Duplicate integration"):
        discover_integrations(integrations_dir=d)


# ---------------------------------------------------------------------------
# Template variables stay literal at this layer
# ---------------------------------------------------------------------------


def test_template_variables_left_literal_at_discovery(tmp_path: Path) -> None:
    d = tmp_path / "cfg"
    d.mkdir()
    _write(
        d / "x.md",
        "---\nintegration: x\ncommands: [plan]\n---\nFeature is {{feature_name}}.\n",
    )
    result = resolve_for("before", "plan", integrations_dir=d)
    assert "{{feature_name}}" in result[0].body


# ---------------------------------------------------------------------------
# Example template must parse
# ---------------------------------------------------------------------------


def test_example_template_parses(tmp_path: Path) -> None:
    """The shipped examples/config/mockups.md.example must be a valid integration."""
    src = Path(__file__).parent.parent / "examples" / "config" / "mockups.md.example"
    if not src.is_file():
        pytest.skip("mockups.md.example not present yet (Phase F)")
    d = tmp_path / "cfg"
    d.mkdir()
    (d / "mockups.md").write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    result = discover_integrations(integrations_dir=d)
    assert len(result) == 1
    integ: Integration = result[0]
    assert integ.name == "mockups"
    assert "spec-specify" in integ.commands
    assert "spec-plan" in integ.commands
