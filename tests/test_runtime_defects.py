"""Feature 083 defect report tests: project-local evidence that blocks a phase (AC-013, AC-014)."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any, NamedTuple

import pytest
from typer.testing import CliRunner

from tests.runtime_support import (
    fixed_clock,
    install,
    make_project,
    make_source,
    restore_write_bits,
    tree_hashes,
    write,
)
from validator.cli import app
from validator.runtime.defects import DefectRequest, report_defect
from validator.runtime.errors import RuntimeDefectError, RuntimeDefectInputError
from validator.runtime.home import RuntimeHome
from validator.runtime.project import dev_project, pin_project

PIPELINE = """# Pipeline — 007-export

| Phase | Status | Completed At |
|-------|--------|--------------|
| Specify | Done | 2026-10-01 10:00 |
| Implement | In Progress | — |
| Test | Pending | — |
"""
ERROR_TEXT = "KeyError: 'receipt'\n```nested fence```"
REPORTS = Path(".specs/tool-defects")


class Pinned(NamedTuple):
    """A pinned consumer project with feature 007-export and its runtime sources."""

    home: RuntimeHome
    checkout: Path
    project: Path
    runtime_id: str


@pytest.fixture
def pinned(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Pinned]:
    """Pin a consumer project whose implement phase is in progress."""
    monkeypatch.setenv("HOME", str(tmp_path / "user-home"))
    home = RuntimeHome((tmp_path / "runtime-home").resolve())
    monkeypatch.setenv("LIVESPEC_HOME", str(home.root))
    checkout = make_source(tmp_path / "checkout")
    runtime_id = install(home, checkout).runtime_id
    project = make_project(tmp_path / "consumer")
    write(project / ".specs/features/007-export/pipeline.md", PIPELINE)
    pin_project(project, runtime_id, home)
    yield Pinned(home, checkout.resolve(), project, runtime_id)
    restore_write_bits(tmp_path)


def _request(
    project: Path,
    home: RuntimeHome,
    feature: str | None = None,
    phase: str | None = None,
    title: str | None = None,
) -> DefectRequest:
    return DefectRequest(
        start=project,
        command="livespec finalize verify",
        error=ERROR_TEXT,
        home=home,
        clock=fixed_clock,
        feature=feature,
        phase=phase,
        title=title,
    )


def _pipeline(project: Path) -> str:
    return (project / ".specs/features/007-export/pipeline.md").read_text()


def test_defect_report_blocks_phase_without_touching_runtimes(
    pinned: Pinned, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC-013: report content, Blocked phase, no LiveSpec root change and no git call."""
    snapshot = pinned.home.snapshot(pinned.runtime_id)
    before = (tree_hashes(snapshot), tree_hashes(pinned.checkout))
    calls: list[str] = []
    real_popen_init = subprocess.Popen.__init__

    # Any: forwards arbitrary Popen arguments unchanged while recording the program name.
    def recording_init(self: subprocess.Popen[Any], args: Any, *rest: Any, **kwargs: Any) -> None:
        calls.append(str(args[0] if isinstance(args, list) else args))
        real_popen_init(self, args, *rest, **kwargs)

    monkeypatch.setattr(subprocess.Popen, "__init__", recording_init)
    title = "Finalize receipt crash"
    request = _request(pinned.project, pinned.home, "007-export", "implement", title)
    result = report_defect(request)
    monkeypatch.undo()
    report = pinned.project / REPORTS / "2026-10-11-finalize-receipt-crash.md"
    assert result.report == report and result.pipeline_updated
    text = report.read_text()
    for expected in ("livespec finalize verify", ERROR_TEXT, pinned.runtime_id, "007-export"):
        assert expected in text
    assert "blocked-by-tool" in text and "livespec runtime upgrade --to <fixed runtime>" in text
    commit = json.loads((pinned.project / ".specs/livespec.lock").read_text())["commit"]
    assert "**Runtime livespec_version:** 21" in text and f"**Runtime commit:** {commit}" in text
    assert "**Phase:** implement" in text and "**Feature:** 007-export" in text
    assert "| Implement | Blocked |" in _pipeline(pinned.project)
    assert (tree_hashes(snapshot), tree_hashes(pinned.checkout)) == before
    assert not [call for call in calls if call.endswith("git")]


def test_same_day_collision_gets_numeric_suffix(pinned: Pinned) -> None:
    """AC-013: an existing report is never overwritten; the new one gets -2."""
    first = report_defect(_request(pinned.project, pinned.home, title="Crash"))
    original = first.report.read_bytes()
    second = report_defect(_request(pinned.project, pinned.home, title="Crash"))
    assert second.report.name == "2026-10-11-crash-2.md"
    assert first.report.read_bytes() == original
    untitled = report_defect(_request(pinned.project, pinned.home))
    assert untitled.report.name == "2026-10-11-livespec-finalize-verify.md"


def test_unpinned_and_dev_identities_and_resume(pinned: Pinned) -> None:
    """AC-014: unpinned records the runtime path; dev records the source and its resume step."""
    (pinned.project / ".specs/livespec.lock").unlink()
    unpinned = report_defect(_request(pinned.project, pinned.home, title="unpinned"))
    text = unpinned.report.read_text()
    assert "**Runtime mode:** unpinned" in text and str(pinned.home.current.resolve()) in text
    assert "livespec runtime pin --runtime <fixed runtime>" in text
    dev_project(pinned.project, pinned.checkout)
    dev = report_defect(_request(pinned.project, pinned.home, title="dev"))
    text = dev.report.read_text()
    assert "**Runtime mode:** dev" in text and f"update the dev checkout {pinned.checkout}" in text


def test_feature_without_phase_and_missing_pipeline(pinned: Pinned) -> None:
    """AC-014: --feature alone leaves the pipeline; a missing pipeline keeps the report."""
    before = _pipeline(pinned.project)
    report_defect(_request(pinned.project, pinned.home, "007-export", None, "no phase"))
    assert _pipeline(pinned.project) == before
    with pytest.raises(RuntimeDefectError, match="phase update failed") as caught:
        report_defect(_request(pinned.project, pinned.home, "999-none", "implement", "orphan"))
    assert Path(caught.value.report_path).is_file()


def test_cli_usage_and_failure_exit_codes(pinned: Pinned, monkeypatch: pytest.MonkeyPatch) -> None:
    """AC-014: --phase without --feature exits 2 with no write; failed update exits 1."""
    base = ["runtime", "defect", "--command", "x", "--error", "boom", "--project"]
    usage = [*base, str(pinned.project), "--phase", "implement"]
    monkeypatch.setattr(sys, "argv", ["livespec", *usage])
    result = CliRunner().invoke(app, usage)
    assert result.exit_code == 2 and not (pinned.project / REPORTS).exists()
    failing = [*base, str(pinned.project), "--feature", "999-none", "--phase", "implement"]
    monkeypatch.setattr(sys, "argv", ["livespec", *failing])
    result = CliRunner().invoke(app, failing)
    assert result.exit_code == 1 and "report kept" in result.stderr
    assert len(list((pinned.project / REPORTS).iterdir())) == 1


def _headings(text: str) -> list[str]:
    """Markdown heading lines outside fenced blocks (a fence closes on its own marker)."""
    headings: list[str] = []
    fence = ""
    for line in text.splitlines():
        marker = re.match(r"^(`{3,})", line)
        if fence:
            fence = "" if line.strip() == fence else fence
        elif marker:
            fence = marker.group(1)
        elif line.startswith("#"):
            headings.append(line)
    return headings


@pytest.mark.parametrize(
    "feature",
    ["../../outside", "/tmp/elsewhere", "007-export/../../x", "a/b", "..", "."],
)
def test_unsafe_feature_is_refused_before_any_write(
    pinned: Pinned, monkeypatch: pytest.MonkeyPatch, feature: str
) -> None:
    """Audit #7: traversal, absolute or separator feature values exit 2 and write nothing."""
    before = _pipeline(pinned.project)
    with pytest.raises(RuntimeDefectInputError):
        report_defect(_request(pinned.project, pinned.home, feature, "implement", "t"))
    args = ["runtime", "defect", "--command", "x", "--error", "y", "--project"]
    args += [str(pinned.project), "--feature", feature, "--phase", "implement"]
    monkeypatch.setattr(sys, "argv", ["livespec", *args])
    result = CliRunner().invoke(app, args)
    assert result.exit_code == 2 and "nothing written" in result.stderr
    assert not (pinned.project / REPORTS).exists() and _pipeline(pinned.project) == before


def test_unknown_phase_is_refused_before_any_write(pinned: Pinned) -> None:
    """Audit #7: a phase outside the pipeline phases is refused with no report."""
    with pytest.raises(RuntimeDefectInputError):
        report_defect(_request(pinned.project, pinned.home, "007-export", "deploy", "t"))
    assert not (pinned.project / REPORTS).exists()


def test_report_renders_untrusted_text_safely(pinned: Pinned) -> None:
    """Audit #8: newline/backtick title, command and error cannot forge report structure."""
    request = DefectRequest(
        start=pinned.project,
        command="run `x`\n# Forged command heading",
        error="boom ```` fence\n## Forged error heading",
        home=pinned.home,
        clock=fixed_clock,
        title="Line one\n## Forged title heading",
    )
    text = report_defect(request).report.read_text()
    assert _headings(text) == [
        "# Tool defect: Line one ## Forged title heading",
        "## Command",
        "## Error",
        "## Resume",
    ]
    assert "```text\nrun `x`\n# Forged command heading\n```\n" in text
    assert "`````text\nboom ```` fence\n## Forged error heading\n`````\n" in text


def test_symlinked_features_dir_is_refused_before_any_write(pinned: Pinned, tmp_path: Path) -> None:
    """Audit round 2 #1: a features dir redirected outside the project writes nothing."""
    outside = tmp_path / "outside-features"
    features = pinned.project / ".specs" / "features"
    features.rename(outside)
    features.symlink_to(outside, target_is_directory=True)
    before = (outside / "007-export" / "pipeline.md").read_text()
    with pytest.raises(RuntimeDefectInputError):
        report_defect(_request(pinned.project, pinned.home, "007-export", "implement", "t"))
    assert not (pinned.project / REPORTS).exists()
    assert (outside / "007-export" / "pipeline.md").read_text() == before


def test_title_html_cannot_hide_report_content(pinned: Pinned) -> None:
    """Audit round 2 #2: an HTML comment opener in the title is escaped literally."""
    request = DefectRequest(
        start=pinned.project,
        command="livespec finalize verify",
        error="boom",
        home=pinned.home,
        clock=fixed_clock,
        title="Crash <!-- hidden & more",
    )
    text = report_defect(request).report.read_text()
    assert "# Tool defect: Crash &lt;!-- hidden &amp; more" in text
    assert "<!--" not in text
