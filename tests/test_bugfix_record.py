"""`livespec bugfix record` writes the trace once and only when eligible (084 AC-012)."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.bugfix_support import FEATURE, FIXED, SPEC, TEST, BugfixProject, make_project


@pytest.fixture
def project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> BugfixProject:
    built = make_project(tmp_path)
    built.write("tests/test_calc.py", TEST)
    monkeypatch.chdir(built.root)
    return built


def _record(project: BugfixProject, red: str, green: str, *extra: str) -> int:
    args = ("--feature", FEATURE, "--red", red, "--green", green, "--summary", "add sums")
    return project.run("bugfix", "record", *args, *extra).exit_code


def _receipts(project: BugfixProject) -> tuple[str, str]:
    _, red = project.capture("red")
    project.write("calc.py", FIXED)
    _, green = project.capture("green")
    return red, green


def test_eligible_fix_is_recorded_once(project: BugfixProject) -> None:
    red, green = _receipts(project)
    changelog = project.feature_dir / "changelog.md"
    implementation = project.feature_dir / "implementation.md"

    assert _record(project, red, green, "--requirement", "AC-001") == 0

    entry = changelog.read_text()
    red_rel = Path(red).relative_to(project.root.resolve()).as_posix()
    green_rel = Path(green).relative_to(project.root.resolve()).as_posix()
    assert "— [Bugfix]: add sums" in entry and "- **Type:** Bugfix" in entry
    assert "- **Spec modified:** No" in entry and "- **AC impacted:** AC-001" in entry
    assert red_rel in entry and green_rel in entry
    table = implementation.read_text()
    assert "## Bugfix Receipts" in table
    assert f"| AC-001 | `tests/test_calc.py::test_add` | `{red_rel}` | `{green_rel}` |" in table

    snapshot = (changelog.read_bytes(), implementation.read_bytes())
    assert _record(project, red, green, "--requirement", "AC-001") == 0
    assert (changelog.read_bytes(), implementation.read_bytes()) == snapshot


def test_second_bugfix_appends_a_row_to_the_existing_table(project: BugfixProject) -> None:
    red, green = _receipts(project)
    assert _record(project, red, green) == 0
    project.write("calc.py", FIXED + "\n")
    _, green_two = project.capture("green")

    assert _record(project, red, green_two) == 0

    table = (project.feature_dir / "implementation.md").read_text()
    assert table.count("## Bugfix Receipts") == 1
    assert table.count("| implementation |") == 2


def test_repeat_is_a_noop_even_when_spec_links_the_implementation_map(
    project: BugfixProject,
) -> None:
    project.write(f".specs/features/{FEATURE}/spec.md", SPEC + "\nRead [map](implementation.md).\n")
    red, green = _receipts(project)
    assert _record(project, red, green, "--base", "HEAD") == 0
    assert "- **Base revision:** HEAD" in (project.feature_dir / "changelog.md").read_text()
    snapshot = sorted((p.name, p.read_bytes()) for p in project.feature_dir.iterdir())

    args = ("--feature", FEATURE, "--red", red, "--green", green, "--summary", "again")
    result = project.run("bugfix", "record", *args)

    assert result.exit_code == 0 and "already recorded" in result.output
    assert sorted((p.name, p.read_bytes()) for p in project.feature_dir.iterdir()) == snapshot


def test_ineligible_fix_writes_nothing(project: BugfixProject) -> None:
    red, green = _receipts(project)
    project.write(f".specs/features/{FEATURE}/spec.md", SPEC.replace("their sum", "a total"))
    before = {path: path.read_bytes() for path in project.feature_dir.iterdir() if path.is_file()}

    assert _record(project, red, green) == 1
    assert {path: path.read_bytes() for path in before} == before
