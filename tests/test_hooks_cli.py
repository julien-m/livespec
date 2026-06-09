# LiveSpec traceability anchors
# @spec(AC-004)
# @spec(FR-010)

"""End-to-end CLI tests for `livespec hooks resolve` and `livespec integrations list`."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from validator.cli import app
from validator.integrations import _reset_warnings_for_tests


@pytest.fixture(autouse=True)
def _isolate_user_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect ~/.config/livespec to a tmp dir per test (autouse).

    This prevents test pollution from the developer's real user config and
    ensures absence-tolerance scenarios are reproducible.
    """
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.setattr(Path, "home", lambda: fake_home)
    _reset_warnings_for_tests()
    # Re-import for changed defaults (module-level constants captured Path.home()
    # at import time). Reload via monkeypatching the module constants directly.
    import validator.hook_resolver as hr
    import validator.integrations as integ

    monkeypatch.setattr(integ, "INTEGRATIONS_DIR", fake_home / ".config" / "livespec")
    monkeypatch.setattr(
        hr,
        "GLOBAL_HOOKS_DIR",
        fake_home / ".claude" / "livespec" / "hooks",
    )
    return fake_home


runner = CliRunner()


def test_hooks_resolve_absent_emits_empty_stdout_exit_zero() -> None:
    result = runner.invoke(app, ["hooks", "resolve", "--event", "before", "--command", "plan"])
    assert result.exit_code == 0
    assert result.stdout == ""
    assert result.stderr == ""


def test_hooks_resolve_unknown_command_warns_and_exits_zero() -> None:
    result = runner.invoke(app, ["hooks", "resolve", "--event", "before", "--command", "bogus"])
    assert result.exit_code == 0
    assert result.stdout == ""
    assert "unknown command" in result.stderr


def test_hooks_resolve_unknown_event_warns_and_exits_zero() -> None:
    result = runner.invoke(app, ["hooks", "resolve", "--event", "weird", "--command", "plan"])
    assert result.exit_code == 0
    assert "unknown event" in result.stderr


def test_hooks_resolve_active_integration_returns_body(
    tmp_path: Path, _isolate_user_config: Path
) -> None:
    cfg = _isolate_user_config / ".config" / "livespec"
    cfg.mkdir(parents=True)
    marker = "MOCKUPS_INTEGRATION_MARKER_abc123"
    (cfg / "mockups.md").write_text(
        f"---\nintegration: mockups\ncommands: [plan]\n---\n{marker}\n",
        encoding="utf-8",
    )
    result = runner.invoke(app, ["hooks", "resolve", "--event", "before", "--command", "plan"])
    assert result.exit_code == 0
    assert marker in result.stdout


def test_hooks_resolve_accepts_hyphenated_command_alias(
    tmp_path: Path, _isolate_user_config: Path
) -> None:
    cfg = _isolate_user_config / ".config" / "livespec"
    cfg.mkdir(parents=True)
    marker = "ALIAS_INTEGRATION_MARKER"
    (cfg / "alias.md").write_text(
        f"---\nintegration: alias\ncommands: [/spec-plan]\n---\n{marker}\n",
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        ["hooks", "resolve", "--event", "before", "--command", "/spec-plan"],
    )

    assert result.exit_code == 0
    assert marker in result.stdout


def test_integrations_list_empty(tmp_path: Path) -> None:
    result = runner.invoke(app, ["integrations", "list"])
    assert result.exit_code == 0
    assert "No user integrations" in result.stdout


def test_integrations_list_one(_isolate_user_config: Path) -> None:
    cfg = _isolate_user_config / ".config" / "livespec"
    cfg.mkdir(parents=True)
    (cfg / "mockups.md").write_text(
        "---\nintegration: mockups\ncommands: [specify, plan]\norder: 50\n---\nbody\n",
        encoding="utf-8",
    )
    result = runner.invoke(app, ["integrations", "list"])
    assert result.exit_code == 0
    assert "mockups" in result.stdout
    assert "spec-specify,spec-plan" in result.stdout
