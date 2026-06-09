"""Tests for `livespec ui-runner` CLI surface (Feature 037 — fix-up).

Validates that `livespec ui-runner check` and `livespec ui-runner dispatch`
expose the dispatcher correctly for client projects that have LiveSpec
installed globally but do not have validator/*.py in their tree.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from validator.cli import app

runner = CliRunner()


def test_ui_runner_check_help_lists_subcommands() -> None:
    """`livespec ui-runner --help` lists check + dispatch."""
    result = runner.invoke(app, ["ui-runner", "--help"])
    assert result.exit_code == 0
    assert "check" in result.stdout
    assert "dispatch" in result.stdout


def test_ui_runner_check_json_returns_registry(tmp_path: Path) -> None:
    """`livespec ui-runner check --json --project-dir <empty>` returns the registry."""
    # No surfaces.yaml → legacy single playwright surface synthesised.
    result = runner.invoke(
        app,
        ["ui-runner", "check", "--json", "--project-dir", str(tmp_path)],
    )
    # exit code 2 because no playwright in tmp_path, but JSON must be valid
    assert result.exit_code == 2
    payload = json.loads(result.stdout)
    assert payload["status"] == "BLOCKED"
    assert set(payload["registry"]) == {"playwright", "xcuitest", "maestro"}
    assert len(payload["surfaces"]) == 1
    assert payload["surfaces"][0]["runner"] == "playwright"


def test_ui_runner_check_human_output(tmp_path: Path) -> None:
    """`livespec ui-runner check` produces human-readable output."""
    result = runner.invoke(
        app,
        ["ui-runner", "check", "--project-dir", str(tmp_path)],
    )
    assert result.exit_code == 2
    assert "Phase 4.5 preflight:" in result.stdout
    assert "Handlers:" in result.stdout
    assert "playwright" in result.stdout
    assert "xcuitest" in result.stdout
    assert "maestro" in result.stdout


def test_ui_runner_dispatch_requires_screens(tmp_path: Path) -> None:
    """`livespec ui-runner dispatch` exits 2 when no screens supplied."""
    result = runner.invoke(
        app,
        [
            "ui-runner",
            "dispatch",
            "--project-dir",
            str(tmp_path),
            "--feature-dir",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 2


def test_ui_runner_check_with_xcuitest_surface(tmp_path: Path) -> None:
    """A surfaces.yaml declaring xcuitest produces a typed BLOCKED reason on Linux/non-mac."""
    specs = tmp_path / ".specs"
    specs.mkdir()
    (specs / "surfaces.yaml").write_text(
        """
surfaces:
  - id: ios-app
    runner: xcuitest
    platform: ios
    path: .
    testDir: STRAPTUITests
""",
        encoding="utf-8",
    )
    result = runner.invoke(
        app,
        ["ui-runner", "check", "--json", "--project-dir", str(tmp_path)],
    )
    payload = json.loads(result.stdout)
    # On macOS may be READY; on Linux always BLOCKED — at minimum surface must be parsed
    assert payload["surfaces"], "surface must be discovered from surfaces.yaml"
    surface = payload["surfaces"][0]
    assert surface["id"] == "ios-app"
    assert surface["runner"] == "xcuitest"


@pytest.mark.parametrize("runner_name", ["playwright", "xcuitest", "maestro"])
def test_ui_runner_check_registry_contains(runner_name: str, tmp_path: Path) -> None:
    """Registry must always include the three core runners."""
    result = runner.invoke(
        app,
        ["ui-runner", "check", "--json", "--project-dir", str(tmp_path)],
    )
    payload = json.loads(result.stdout)
    assert runner_name in payload["registry"]


def test_ui_runner_scaffold_ios_copies_template(tmp_path: Path) -> None:
    """scaffold --target ios copies LSSampleUITests.swift into the project."""
    # Create a UITests directory so scaffold uses it.
    uitests = tmp_path / "MyAppUITests"
    uitests.mkdir()

    result = runner.invoke(
        app,
        ["ui-runner", "scaffold", "--target", "ios", "--project-dir", str(tmp_path)],
    )
    assert result.exit_code == 0
    assert (uitests / "LSSampleUITests.swift").exists()
    assert "Scaffolded ios runner template" in result.stdout


def test_ui_runner_scaffold_ios_skips_existing_without_force(tmp_path: Path) -> None:
    """Existing files are skipped unless --force is passed."""
    uitests = tmp_path / "MyAppUITests"
    uitests.mkdir()
    existing = uitests / "LSSampleUITests.swift"
    existing.write_text("// my custom test", encoding="utf-8")

    result = runner.invoke(
        app,
        ["ui-runner", "scaffold", "--target", "ios", "--project-dir", str(tmp_path)],
    )
    assert result.exit_code == 0
    assert existing.read_text(encoding="utf-8") == "// my custom test"


def test_ui_runner_scaffold_ios_force_overwrites(tmp_path: Path) -> None:
    """--force overwrites existing template files."""
    uitests = tmp_path / "MyAppUITests"
    uitests.mkdir()
    existing = uitests / "LSSampleUITests.swift"
    existing.write_text("// stale", encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "ui-runner",
            "scaffold",
            "--target",
            "ios",
            "--project-dir",
            str(tmp_path),
            "--force",
        ],
    )
    assert result.exit_code == 0
    assert "XCUITest" in existing.read_text(encoding="utf-8")


def test_ui_runner_scaffold_ios_falls_back_to_uitests_dir(tmp_path: Path) -> None:
    """When no *UITests/ glob match exists, scaffold creates UITests/."""
    result = runner.invoke(
        app,
        ["ui-runner", "scaffold", "--target", "ios", "--project-dir", str(tmp_path)],
    )
    assert result.exit_code == 0
    assert (tmp_path / "UITests" / "LSSampleUITests.swift").exists()


def test_ui_runner_converge_requires_screens(tmp_path: Path) -> None:
    """converge without screen args exits with code 2 (mirrors dispatch)."""
    result = runner.invoke(
        app,
        [
            "ui-runner",
            "converge",
            "--project-dir",
            str(tmp_path),
            "--feature-dir",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 2


def test_ui_runner_converge_help_lists_max_iterations() -> None:
    """converge --help mentions --max-iterations to make the loop discoverable.

    Strip ANSI escape codes before asserting — rich/typer renders coloured
    output on CI runners (TTY heuristic differs from local), which fragments
    the flag name across the rendered string.
    """
    import re

    result = runner.invoke(app, ["ui-runner", "converge", "--help"])
    assert result.exit_code == 0
    cleaned = re.sub(r"\x1b\[[0-9;]*m", "", result.stdout)
    assert "max-iterations" in cleaned


# --------------------------------------------------------------------------
# Auto-discovery of screens for `converge --all` / `converge --feature`.
# --------------------------------------------------------------------------


def _make_feature(root: Path, slug: str, status: str, screens_section: str) -> Path:
    """Write a minimal spec.md fixture with a `## Screens` section."""
    fdir = root / ".specs" / "features" / slug
    fdir.mkdir(parents=True, exist_ok=True)
    spec = f"""---
title: "{slug}"
status: "{status}"
---

# {slug}

## Screens

{screens_section}
"""
    (fdir / "spec.md").write_text(spec, encoding="utf-8")
    return fdir


def test_discover_screens_table_format(tmp_path: Path) -> None:
    """Markdown table with screen IDs in the first column is parsed."""
    from validator.cli_commands.ui_runner_cmd import _discover_screens_in_feature

    fdir = _make_feature(
        tmp_path,
        "001-test",
        "Implemented",
        """| Screen | Status | Reference |
|--------|--------|-----------|
| iphone-home | Modified | (link) |
| iphone-edit | New | (link) |
""",
    )
    screens = _discover_screens_in_feature(fdir)
    assert screens == ["iphone-home", "iphone-edit"]


def test_discover_screens_bullet_format(tmp_path: Path) -> None:
    """Bullet form `- **id.png** — ...` is also recognised."""
    from validator.cli_commands.ui_runner_cmd import _discover_screens_in_feature

    fdir = _make_feature(
        tmp_path,
        "003-haptic",
        "Implemented",
        """- **watch-rest-timer.png** — Main rest timer display
- **watch-pre-alert.png** — Pre-alert state
""",
    )
    screens = _discover_screens_in_feature(fdir)
    assert "watch-rest-timer" in screens
    assert "watch-pre-alert" in screens


def test_discover_screens_skips_draft_features(tmp_path: Path) -> None:
    """`--all` honours feature status frontmatter (Draft features are dropped)."""
    from validator.cli_commands.ui_runner_cmd import _discover_screens_all

    _make_feature(
        tmp_path,
        "001-impl",
        "Implemented",
        """| Screen | Status |
|--------|--------|
| home | New |
""",
    )
    _make_feature(
        tmp_path,
        "002-draft",
        "Draft",
        """| Screen | Status |
|--------|--------|
| should-not-appear | New |
""",
    )
    pairs = _discover_screens_all(tmp_path)
    slugs = {f for f, _ in pairs}
    screens = [s for _, s in pairs]
    assert "001-impl" in slugs
    assert "002-draft" not in slugs
    assert "should-not-appear" not in screens


def test_discover_screens_empty_when_no_section(tmp_path: Path) -> None:
    """A spec.md without `## Screens` yields zero discoveries."""
    from validator.cli_commands.ui_runner_cmd import _discover_screens_in_feature

    fdir = tmp_path / ".specs" / "features" / "001-none"
    fdir.mkdir(parents=True)
    (fdir / "spec.md").write_text("---\nstatus: Implemented\n---\n# 001\n", encoding="utf-8")
    assert _discover_screens_in_feature(fdir) == []


def test_converge_all_blocks_with_explicit_screens(tmp_path: Path) -> None:
    """--all and positional screens are mutually exclusive."""
    result = runner.invoke(
        app,
        [
            "ui-runner",
            "converge",
            "iphone-home",
            "--all",
            "--project-dir",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 2


def test_converge_all_blocks_when_no_screens_discovered(tmp_path: Path) -> None:
    """--all errors clearly when no eligible feature has a Screens table."""
    result = runner.invoke(
        app,
        ["ui-runner", "converge", "--all", "--project-dir", str(tmp_path)],
    )
    assert result.exit_code == 2
