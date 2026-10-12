"""Feature 083 selection tests: pin, upgrade and dev (AC-006..AC-009, AC-011)."""

from __future__ import annotations

import json
import os
import shutil
from collections.abc import Iterator
from pathlib import Path
from typing import NamedTuple

import pytest

from tests.runtime_support import (
    commit_all,
    git,
    install,
    link_into,
    make_project,
    make_source,
    restore_write_bits,
    tree_hashes,
    write,
)
from validator.runtime import links as links_module
from validator.runtime.errors import (
    RuntimeLockError,
    RuntimeSelectionError,
    RuntimeSnapshotError,
)
from validator.runtime.home import RuntimeHome
from validator.runtime.project import dev_project, pin_project, upgrade_project


class Runtimes(NamedTuple):
    """Two installed runtimes (VERSION 21 then 22; current = 22) and their checkout."""

    home: RuntimeHome
    checkout: Path
    v21: str
    v22: str


@pytest.fixture
def runtimes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Runtimes]:
    """Install VERSION 21 and 22 snapshots of a temporary checkout."""
    monkeypatch.setenv("HOME", str(tmp_path / "user-home"))
    home = RuntimeHome((tmp_path / "runtime-home").resolve())
    checkout = make_source(tmp_path / "checkout")
    v21 = install(home, checkout).runtime_id
    write(checkout / "VERSION", "22\n")
    commit_all(checkout, "v22")
    v22 = install(home, checkout).runtime_id
    yield Runtimes(home, checkout.resolve(), v21, v22)
    restore_write_bits(tmp_path)


def _consumer(tmp_path: Path, checkout: Path, version: int = 21) -> Path:
    project = make_project(tmp_path / "consumer", version)
    write(project / ".specs/.livespec-path", f"{checkout}\n")
    link_into(project, "skills/spec-check", checkout / ".agent-sync/skills/spec-check")
    link_into(project, "rules/commands.md", checkout / ".agent-sync/rules/livespec/commands.md")
    write(project / ".agent-sync.local/skills/team-notes/SKILL.md", "# team notes\n")
    link_into(project, "skills/foreign", tmp_path)
    return project


def _snapshot(runtimes: Runtimes, runtime_id: str) -> Path:
    return runtimes.home.snapshot(runtime_id)


def test_pin_current_writes_portable_lock_and_retargets_links(
    runtimes: Runtimes, tmp_path: Path
) -> None:
    """AC-006/AC-007: exact lock keys, machine-local path, owned links moved, others kept."""
    project = _consumer(tmp_path, runtimes.checkout, version=22)
    notes = tree_hashes(project / ".agent-sync.local/skills/team-notes")
    result = pin_project(project, "current", runtimes.home)
    lock = json.loads((project / ".specs/livespec.lock").read_text())
    assert set(lock) == {"schema", "mode", "runtime_id", "livespec_version", "commit"}
    assert lock["mode"] == "pinned" and lock["runtime_id"] == runtimes.v22
    assert (project / ".specs/livespec.lock").read_text().endswith("}\n")
    snapshot = _snapshot(runtimes, runtimes.v22)
    assert (project / ".specs/.livespec-path").read_text().strip() == str(snapshot)
    skill = project / ".agent-sync.local/skills/spec-check"
    assert Path(os.readlink(skill)) == snapshot / ".agent-sync/skills/spec-check"
    rule = project / ".agent-sync.local/rules/commands.md"
    assert Path(os.readlink(rule)) == snapshot / ".agent-sync/rules/livespec/commands.md"
    assert tree_hashes(project / ".agent-sync.local/skills/team-notes") == notes
    assert Path(os.readlink(project / ".agent-sync.local/skills/foreign")) == tmp_path
    assert result.links.missing == () and len(result.links.retargeted) == 2


def test_link_missing_in_snapshot_is_reported_unchanged(runtimes: Runtimes, tmp_path: Path) -> None:
    """AC-007: an owned link absent from the snapshot stays and is listed as missing."""
    project = _consumer(tmp_path, runtimes.checkout)
    write(runtimes.checkout / ".agent-sync/skills/only-here/SKILL.md", "# local\n")
    only = link_into(
        project, "skills/only-here", runtimes.checkout / ".agent-sync/skills/only-here"
    )
    result = pin_project(project, runtimes.v21, runtimes.home)
    assert result.links.missing == (".agent-sync.local/skills/only-here",)
    assert Path(os.readlink(only)) == runtimes.checkout / ".agent-sync/skills/only-here"
    assert len(result.links.retargeted) == 2


def test_fresh_machine_rematerializes_path_without_changing_lock(
    runtimes: Runtimes, tmp_path: Path
) -> None:
    """AC-006: pin --runtime <locked id> recreates .livespec-path; lock bytes unchanged."""
    project = _consumer(tmp_path, runtimes.checkout)
    pin_project(project, runtimes.v21, runtimes.home)
    lock_bytes = (project / ".specs/livespec.lock").read_bytes()
    (project / ".specs/.livespec-path").unlink()
    shutil.rmtree(project / ".agent-sync.local")
    snapshot = _snapshot(runtimes, runtimes.v21)
    link_into(project, "skills/spec-check", snapshot / ".agent-sync/skills/spec-check")
    result = pin_project(project, runtimes.v21, runtimes.home)
    assert (project / ".specs/livespec.lock").read_bytes() == lock_bytes
    assert (project / ".specs/.livespec-path").read_text().strip() == str(snapshot)
    assert result.links.unchanged == (".agent-sync.local/skills/spec-check",)
    assert not (project / ".agent-sync.local/rules").exists()


def test_pin_replaces_dev_lock_and_requires_a_runtime(runtimes: Runtimes, tmp_path: Path) -> None:
    """AC-006: previous lock reported; no --runtime and no current exits with no write."""
    project = _consumer(tmp_path, runtimes.checkout)
    dev_project(project, runtimes.checkout)
    result = pin_project(project, runtimes.v21, runtimes.home)
    assert isinstance(result.previous_lock, dict) and result.previous_lock["mode"] == "dev"
    runtimes.home.current.unlink()
    before = tree_hashes(project)
    with pytest.raises(RuntimeSelectionError, match="livespec runtime install"):
        pin_project(project, "current", runtimes.home)
    assert tree_hashes(project) == before


def test_unsafe_pins_change_nothing(runtimes: Runtimes, tmp_path: Path) -> None:
    """AC-007/AC-008: uninstalled, corrupted or older runtimes are refused with no write."""
    project = _consumer(tmp_path, runtimes.checkout, version=22)
    before = tree_hashes(project)
    with pytest.raises(RuntimeSnapshotError):
        pin_project(project, "21-cccccccccccc", runtimes.home)
    with pytest.raises(RuntimeSelectionError, match="newer than runtime"):
        pin_project(project, runtimes.v21, runtimes.home)
    target = _snapshot(runtimes, runtimes.v22) / "system/tool-project-boundary.md"
    target.chmod(0o644)
    target.write_text("tampered\n")
    with pytest.raises(RuntimeSnapshotError, match="digest"):
        pin_project(project, runtimes.v22, runtimes.home)
    assert tree_hashes(project) == before


def test_pin_warns_when_livespec_path_is_not_ignored(runtimes: Runtimes, tmp_path: Path) -> None:
    """AC-006: a warning, never an ignore-file edit, when .livespec-path is tracked-able."""
    project = _consumer(tmp_path, runtimes.checkout)
    git(project, "init", "-q")
    assert pin_project(project, runtimes.v21, runtimes.home).warnings
    assert not (project / ".gitignore").exists()
    write(project / ".gitignore", ".specs/.livespec-path\n")
    assert pin_project(project, runtimes.v21, runtimes.home).warnings == ()
    assert (project / ".gitignore").read_text() == ".specs/.livespec-path\n"


def test_upgrade_moves_references_and_reports_migration(runtimes: Runtimes, tmp_path: Path) -> None:
    """AC-009: lock, path and links move to the new runtime; migration_required is reported."""
    project = _consumer(tmp_path, runtimes.checkout)
    pin_project(project, runtimes.v21, runtimes.home)
    result = upgrade_project(project, runtimes.v22, runtimes.home)
    payload = result.to_dict()
    assert payload["old_runtime_id"] == runtimes.v21 and payload["new_runtime_id"] == runtimes.v22
    assert payload["migration_required"] is True and payload["recovery"] == "/spec-migrate"
    snapshot = _snapshot(runtimes, runtimes.v22)
    assert (project / ".specs/.livespec-path").read_text().strip() == str(snapshot)
    assert os.readlink(project / ".agent-sync.local/skills/spec-check").startswith(str(snapshot))
    write(project / ".specs/livespec-version", "22\n")
    same = upgrade_project(project, runtimes.v22, runtimes.home)
    assert same.changed is False and same.migration_required is False


def test_upgrade_noop_verifies_target_first(runtimes: Runtimes, tmp_path: Path) -> None:
    """AC-009: same id is a byte-identical no-op, but a corrupted pinned snapshot exits 1."""
    project = _consumer(tmp_path, runtimes.checkout, version=22)
    pin_project(project, runtimes.v22, runtimes.home)
    before = tree_hashes(project)
    assert upgrade_project(project, "current", runtimes.home).changed is False
    assert tree_hashes(project) == before
    target = _snapshot(runtimes, runtimes.v22) / "system/tool-project-boundary.md"
    target.chmod(0o644)
    target.write_text("tampered\n")
    with pytest.raises(RuntimeSnapshotError):
        upgrade_project(project, runtimes.v22, runtimes.home)


def test_upgrade_requires_pinned_lock_and_newer_target(runtimes: Runtimes, tmp_path: Path) -> None:
    """AC-008/AC-009: no lock or dev lock directs to pin; an older target is refused."""
    project = _consumer(tmp_path, runtimes.checkout, version=22)
    before = tree_hashes(project)
    with pytest.raises(RuntimeLockError, match="livespec runtime pin"):
        upgrade_project(project, runtimes.v22, runtimes.home)
    assert tree_hashes(project) == before
    dev_project(project, runtimes.checkout)
    dev_state = tree_hashes(project)
    with pytest.raises(RuntimeLockError, match="livespec runtime pin"):
        upgrade_project(project, runtimes.v22, runtimes.home)
    assert tree_hashes(project) == dev_state
    pin_project(project, runtimes.v22, runtimes.home)
    pinned_state = tree_hashes(project)
    with pytest.raises(RuntimeSelectionError, match="newer than runtime"):
        upgrade_project(project, runtimes.v21, runtimes.home)
    assert tree_hashes(project) == pinned_state


def test_dev_lock_source_forms_and_refusal(runtimes: Runtimes, tmp_path: Path) -> None:
    """AC-011: '.' for the repository itself, relative inside, absolute outside, root check."""
    repo = runtimes.checkout
    (repo / ".specs").mkdir(exist_ok=True)
    assert dev_project(repo, repo).lock["source"] == "."
    nested = make_source(tmp_path / "consumer-with-checkout" / "vendor" / "livespec")
    project = make_project(tmp_path / "consumer-with-checkout")
    assert dev_project(project, nested).lock["source"] == "vendor/livespec"
    outside = _consumer(tmp_path, runtimes.checkout)
    result = dev_project(outside, runtimes.checkout)
    assert result.lock == {"schema": 1, "mode": "dev", "source": str(runtimes.checkout)}
    assert os.readlink(outside / ".agent-sync.local/skills/spec-check").startswith(str(repo))
    assert (outside / ".specs/.livespec-path").read_text().strip() == str(runtimes.checkout)
    before = tree_hashes(outside)
    with pytest.raises(RuntimeSelectionError, match="not a LiveSpec root"):
        dev_project(outside, tmp_path / "user-home")
    assert tree_hashes(outside) == before


def test_pin_replaces_lock_pinned_to_another_runtime(runtimes: Runtimes, tmp_path: Path) -> None:
    """AC-006: pinning another installed runtime replaces the lock and reports the previous one."""
    project = _consumer(tmp_path, runtimes.checkout)
    pin_project(project, runtimes.v21, runtimes.home)
    result = pin_project(project, runtimes.v22, runtimes.home)
    assert isinstance(result.previous_lock, dict)
    assert result.previous_lock["runtime_id"] == runtimes.v21
    lock = json.loads((project / ".specs/livespec.lock").read_text())
    assert lock["mode"] == "pinned" and lock["runtime_id"] == runtimes.v22
    snapshot = _snapshot(runtimes, runtimes.v22)
    assert (project / ".specs/.livespec-path").read_text().strip() == str(snapshot)


def test_broken_links_need_trusted_provenance(runtimes: Runtimes, tmp_path: Path) -> None:
    """Audit #11: a broken link is owned only when its root is the recorded .livespec-path."""
    project = make_project(tmp_path / "consumer")
    vanished = tmp_path / "unrelated-root"
    foreign_text = str(vanished / ".agent-sync/skills/spec-check")
    foreign = link_into(project, "skills/foreign-broken", Path(foreign_text))
    recorded = tmp_path / "deleted-runtime"
    write(project / ".specs/.livespec-path", f"{recorded}\n")
    trusted = link_into(project, "skills/spec-check", recorded / ".agent-sync/skills/spec-check")
    result = pin_project(project, runtimes.v21, runtimes.home)
    snapshot = runtimes.home.snapshot(runtimes.v21)
    assert os.readlink(foreign) == foreign_text
    assert Path(os.readlink(trusted)) == snapshot / ".agent-sync/skills/spec-check"
    assert result.links.retargeted == (".agent-sync.local/skills/spec-check",)


def test_selection_failure_restores_previous_state(
    runtimes: Runtimes, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Audit #12: a failure mid-publication restores lock, .livespec-path and links."""
    project = _consumer(tmp_path, runtimes.checkout)
    pin_project(project, runtimes.v21, runtimes.home)
    before = tree_hashes(project)
    calls: list[Path] = []
    real = links_module.replace_symlink

    def failing(path: Path, target: Path | str) -> None:
        """Retarget the first link, then fail on the second."""
        calls.append(path)
        if len(calls) == 2:
            raise OSError("injected link failure")
        real(path, target)

    monkeypatch.setattr(links_module, "replace_symlink", failing)
    with pytest.raises(RuntimeSelectionError, match="rolled back"):
        upgrade_project(project, runtimes.v22, runtimes.home)
    monkeypatch.undo()
    assert len(calls) == 2 and tree_hashes(project) == before


def test_lock_is_published_last_and_rollback_failure_is_reported(
    runtimes: Runtimes, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Audit round 2 #4/#5: links change before the lock; a failed rollback is not hidden."""
    from validator.runtime import project as project_module

    project = _consumer(tmp_path, runtimes.checkout)
    pin_project(project, runtimes.v21, runtimes.home)
    lock_path = project / ".specs" / "livespec.lock"
    old_lock = lock_path.read_bytes()
    real = links_module.replace_symlink
    seen_locks: list[bytes] = []

    def failing_link(path: Path, target: Path | str) -> None:
        """Record the lock visible while links are being written, then fail."""
        seen_locks.append(lock_path.read_bytes())
        raise OSError("injected link failure")

    monkeypatch.setattr(links_module, "replace_symlink", failing_link)
    with pytest.raises(RuntimeSelectionError, match="rolled back"):
        upgrade_project(project, runtimes.v22, runtimes.home)
    assert seen_locks == [old_lock] and lock_path.read_bytes() == old_lock

    calls: list[Path] = []

    def second_fails(path: Path, target: Path | str) -> None:
        """Retarget the first link, then fail so that a rollback is needed."""
        calls.append(path)
        if len(calls) == 2:
            raise OSError("injected link failure")
        real(path, target)

    def failing_restore(path: Path, target: Path | str) -> None:
        """Make the rollback of link texts fail too."""
        raise OSError("injected rollback failure")

    monkeypatch.setattr(links_module, "replace_symlink", second_fails)
    monkeypatch.setattr(project_module, "replace_symlink", failing_restore)
    with pytest.raises(RuntimeSelectionError, match="rollback incomplete"):
        upgrade_project(project, runtimes.v22, runtimes.home)
