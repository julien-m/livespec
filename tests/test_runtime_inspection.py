"""Feature 083 drift detection tests for runtime status and doctor (AC-015..AC-017)."""

from __future__ import annotations

import json
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import NamedTuple

import pytest
from typer.testing import CliRunner

from tests.runtime_support import (
    commit_all,
    install,
    link_into,
    make_project,
    make_source,
    restore_write_bits,
    tree_hashes,
    write,
)
from validator.cli import app
from validator.doctor import run_doctor
from validator.runtime.home import RuntimeHome
from validator.runtime.inspection import runtime_findings
from validator.runtime.models import RuntimeFinding
from validator.runtime.project import dev_project, pin_project
from validator.runtime.snapshot import remove_tree


class Setup(NamedTuple):
    """Two installed snapshots of a git checkout and a running-root stand-in."""

    home: RuntimeHome
    checkout: Path
    pinned: str
    other: str


@pytest.fixture
def setup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Setup]:
    """Install two snapshots; LIVESPEC_HOME points at the temporary home."""
    monkeypatch.setenv("HOME", str(tmp_path / "user-home"))
    home = RuntimeHome((tmp_path / "runtime-home").resolve())
    monkeypatch.setenv("LIVESPEC_HOME", str(home.root))
    checkout = make_source(tmp_path / "checkout")
    pinned = install(home, checkout).runtime_id
    write(checkout / "notes.md", "other\n")
    commit_all(checkout, "other")
    other = install(home, checkout).runtime_id
    yield Setup(home, checkout.resolve(), pinned, other)
    restore_write_bits(tmp_path)


def _codes(findings: list[RuntimeFinding]) -> list[tuple[str, str]]:
    return sorted((item.code, item.severity.value) for item in findings)


def _link_checkout(project: Path, checkout: Path) -> None:
    link_into(project, "skills/spec-check", checkout / ".agent-sync/skills/spec-check")


def _link_snapshot(project: Path, snapshot: Path) -> None:
    link_into(project, "rules/commands.md", snapshot / ".agent-sync/rules/livespec/commands.md")


def test_unpinned_checkout_clean_warning_then_dirty_error(setup: Setup, tmp_path: Path) -> None:
    """AC-015: clean checkout WARNING, dirty ERROR; the check leaves index and files intact."""
    project = make_project(tmp_path / "consumer")
    _link_checkout(project, setup.checkout)
    running = setup.home.snapshot(setup.pinned)
    clean = runtime_findings(project, setup.home, running)
    assert _codes(clean) == [("runtime_checkout_reference", "WARNING")]
    assert str(setup.checkout) in clean[0].message
    write(setup.checkout / "scratch.txt", "dirty\n")
    index = setup.checkout / ".git/index"
    index_before = (index.read_bytes(), index.stat().st_mtime_ns)
    files_before = tree_hashes(setup.checkout)
    dirty = runtime_findings(project, setup.home, running)
    assert _codes(dirty) == [("runtime_checkout_dirty", "ERROR")]
    assert (index.read_bytes(), index.stat().st_mtime_ns) == index_before
    assert tree_hashes(setup.checkout) == files_before


def test_unpinned_snapshot_links_and_cumulative_findings(setup: Setup, tmp_path: Path) -> None:
    """AC-015: snapshot links WARNING; mixed dirty checkout + snapshot yields both."""
    project = make_project(tmp_path / "consumer")
    _link_snapshot(project, setup.home.snapshot(setup.pinned))
    running = setup.home.snapshot(setup.pinned)
    only_snapshot = runtime_findings(project, setup.home, running)
    assert _codes(only_snapshot) == [("runtime_snapshot_links_unpinned", "WARNING")]
    _link_checkout(project, setup.checkout)
    write(setup.checkout / "scratch.txt", "dirty\n")
    assert _codes(runtime_findings(project, setup.home, running)) == [
        ("runtime_checkout_dirty", "ERROR"),
        ("runtime_snapshot_links_unpinned", "WARNING"),
    ]


def test_pinned_drift_findings(setup: Setup, tmp_path: Path) -> None:
    """AC-015/AC-016: mismatch WARNING, checkout rule, executing mismatch, snapshot errors."""
    project = make_project(tmp_path / "consumer")
    _link_snapshot(project, setup.home.snapshot(setup.pinned))
    pin_project(project, setup.pinned, setup.home)
    pinned_root = setup.home.snapshot(setup.pinned)
    assert runtime_findings(project, setup.home, pinned_root) == []
    other_skill = setup.home.snapshot(setup.other) / ".agent-sync/skills/spec-check"
    link_into(project, "skills/spec-check", other_skill)
    assert _codes(runtime_findings(project, setup.home, pinned_root)) == [
        ("runtime_reference_mismatch", "WARNING")
    ]
    link_into(
        project, "skills/spec-implement", setup.checkout / ".agent-sync/skills/spec-implement"
    )
    write(setup.checkout / "scratch.txt", "dirty\n")
    findings = runtime_findings(project, setup.home, setup.checkout)
    assert _codes(findings) == [
        ("runtime_checkout_dirty", "ERROR"),
        ("runtime_executing_mismatch", "ERROR"),
        ("runtime_reference_mismatch", "WARNING"),
    ]
    executing = next(item for item in findings if item.code == "runtime_executing_mismatch")
    assert str(setup.checkout) in executing.message
    assert "PATH" in (executing.suggested_action or "")


def test_missing_or_corrupted_pinned_snapshot_is_error(setup: Setup, tmp_path: Path) -> None:
    """AC-016: manifest commit mismatch, digest mismatch and missing directory are ERRORs."""
    project = make_project(tmp_path / "consumer")
    pin_project(project, setup.pinned, setup.home)
    snapshot = setup.home.snapshot(setup.pinned)
    lock_path = project / ".specs/livespec.lock"
    pinned_lock = lock_path.read_text()
    lock = json.loads(pinned_lock)
    lock["commit"] = lock["commit"][:12] + "0" * (len(lock["commit"]) - 12)
    lock_path.write_text(json.dumps(lock))
    mismatch = runtime_findings(project, setup.home, snapshot)
    assert [(item.code, "differs" in item.message) for item in mismatch] == [
        ("runtime_snapshot_invalid", True)
    ]
    lock_path.write_text(pinned_lock)
    target = snapshot / "system/tool-project-boundary.md"
    target.chmod(0o644)
    target.write_text("tampered\n")
    assert _codes(runtime_findings(project, setup.home, snapshot)) == [
        ("runtime_snapshot_invalid", "ERROR")
    ]
    remove_tree(snapshot)
    assert _codes(runtime_findings(project, setup.home, snapshot)) == [
        ("runtime_snapshot_missing", "ERROR")
    ]


def test_lock_modes_and_quiet_cases(setup: Setup, tmp_path: Path) -> None:
    """AC-016/AC-017: invalid lock ERROR, dev INFO only, LiveSpec root silent."""
    project = make_project(tmp_path / "consumer")
    running = setup.home.snapshot(setup.pinned)
    assert runtime_findings(project, setup.home, running) == []
    lock = write(project / ".specs/livespec.lock", "{broken")
    invalid = runtime_findings(project, setup.home, running)
    assert _codes(invalid) == [("runtime_lock_invalid", "ERROR")]
    assert invalid[0].path == str(lock)
    _link_checkout(project, setup.checkout)
    write(setup.checkout / "scratch.txt", "dirty\n")
    dev_project(project, setup.checkout)
    assert _codes(runtime_findings(project, setup.home, running)) == [("runtime_dev_mode", "INFO")]
    (setup.checkout / ".specs").mkdir(exist_ok=True)
    assert runtime_findings(setup.checkout, setup.home, running) == []
    dev_project(setup.checkout, setup.checkout)
    assert runtime_findings(setup.checkout, setup.home, running) == []


def test_dev_source_not_a_livespec_root_is_an_invalid_lock(setup: Setup, tmp_path: Path) -> None:
    """Plan D-04: a dev lock whose source is not a LiveSpec root is an invalid lock (ERROR)."""
    project = make_project(tmp_path / "consumer")
    write(project / ".specs/livespec.lock", '{"mode": "dev", "schema": 1, "source": "gone"}')
    findings = runtime_findings(project, setup.home, setup.home.snapshot(setup.pinned))
    assert _codes(findings) == [("runtime_dev_source_invalid", "ERROR")]


def test_status_json_and_exit_code(
    setup: Setup, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC-017: JSON fields; exit 1 if and only if an ERROR finding exists."""
    project = make_project(tmp_path / "consumer")
    _link_checkout(project, setup.checkout)
    args = [
        "runtime",
        "status",
        "--project",
        str(project),
        "--home",
        str(setup.home.root),
        "--json",
    ]
    monkeypatch.setattr(sys, "argv", ["livespec", *args])
    clean = CliRunner().invoke(app, args)
    assert clean.exit_code == 0
    payload = json.loads(clean.stdout)
    assert payload["mode"] == "unpinned" and payload["lock"] is None
    assert payload["resolved_root"] == str(setup.home.snapshot(setup.other))
    assert payload["executing_validator"].endswith("validator")
    assert [item["severity"] for item in payload["findings"]] == ["WARNING"]
    write(setup.checkout / "scratch.txt", "dirty\n")
    assert CliRunner().invoke(app, args).exit_code == 1


def test_doctor_reports_the_same_runtime_findings(setup: Setup, tmp_path: Path) -> None:
    """AC-017: doctor contains the shared scanner findings under category runtime."""
    project = make_project(tmp_path / "consumer")
    _link_checkout(project, setup.checkout)
    _link_snapshot(project, setup.home.snapshot(setup.pinned))
    write(setup.checkout / "scratch.txt", "dirty\n")
    report = run_doctor(project)
    runtime = sorted(
        (item.code, item.severity.value) for item in report.findings if item.category == "runtime"
    )
    assert runtime == [
        ("runtime_checkout_dirty", "ERROR"),
        ("runtime_snapshot_links_unpinned", "WARNING"),
    ]
    assert report.status.value == "FAIL"
    (setup.checkout / ".specs").mkdir(exist_ok=True)
    root_report = run_doctor(setup.checkout)
    assert [item for item in root_report.findings if item.category == "runtime"] == []


def test_status_json_in_dev_mode(
    setup: Setup, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC-017: status --json reports mode dev, the lock, the checkout root and one INFO finding."""
    project = make_project(tmp_path / "consumer")
    _link_checkout(project, setup.checkout)
    dev_project(project, setup.checkout)
    args = ["runtime", "status", "--project", str(project), "--home", str(setup.home.root)]
    args.append("--json")
    monkeypatch.setattr(sys, "argv", ["livespec", *args])
    result = CliRunner().invoke(app, args)
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["mode"] == "dev"
    assert payload["lock"] == {"schema": 1, "mode": "dev", "source": str(setup.checkout)}
    assert payload["resolved_root"] == str(setup.checkout)
    assert [(item["code"], item["severity"]) for item in payload["findings"]] == [
        ("runtime_dev_mode", "INFO")
    ]
