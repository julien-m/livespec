"""Cover the format-23 migration and rollback through the real migration executor."""

# @spec AC-010: Observe forward migration and scoped rollback through the shipped executor
#   — .specs/features/122-review-led-delivery/spec.md#ac-010

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path

import pytest

from validator.migration_restore import (
    V22_LEGACY_SCOPE,
    V22_SCOPE,
    V23_SCOPE,
    RestorePointError,
    record,
    restore,
    store_of,
)

REPO = Path(__file__).resolve().parents[1]
VERSION = ".specs/livespec-version"
POLICY = ".specs/recovery-policy.yaml"


def _project(path: Path, version: int) -> Path:
    (path / ".specs").mkdir(parents=True)
    (path / VERSION).write_text(f"{version}\n")
    return path


def _migrate(
    project: Path,
    version: int,
    *,
    inverse: bool = False,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    document = REPO / "migrations" / str(version) / ("inverse.md" if inverse else "migrate.md")
    return subprocess.run(
        ["bash", str(REPO / "scripts/migrate.sh"), str(document), str(project), str(REPO)],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
        env=env,
    )


def _test_tools(tmp_path: Path) -> dict[str, str]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for name in ("cc-hub", "livespec"):
        tool = bin_dir / name
        tool.write_text("#!/bin/sh\nexit 0\n")
        tool.chmod(0o755)
    return {**os.environ, "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}"}


def _check(result: subprocess.CompletedProcess[str]) -> None:
    assert result.returncode == 0, result.stdout + result.stderr


def _read_manifest(project: Path, version: int) -> tuple[Path, dict[str, object]]:
    file = store_of(project, version) / "manifest.json"
    document: dict[str, object] = json.loads(file.read_text())
    return file, document


def test_round_trip_format_21_project_preserves_gitignore_and_unrelated_history(
    tmp_path: Path,
) -> None:
    project = _project(tmp_path / "project", 21)
    subprocess.run(["git", "init", "-q", str(project)], check=True, timeout=15)
    gitignore = project / ".gitignore"
    gitignore.write_bytes(b".local")
    historic_spec = project / ".specs/changelog.md"
    historic_spec.write_text("Before migration\n")
    env = _test_tools(tmp_path)
    _check(_migrate(project, 22, env=env))
    assert (project / VERSION).read_text() == "22\n"
    assert gitignore.read_text().splitlines()[0] == ".local"
    _file, manifest = _read_manifest(project, 22)
    assert "changelog.md" not in json.dumps(manifest)
    for path in (
        ".specs/.migration-restore/22/manifest.json",
        ".specs/conventions/debt-report.md",
        ".specs/conventions/debt.json",
    ):
        check = subprocess.run(
            ["git", "-C", str(project), "check-ignore", "--quiet", path],
            check=False,
            timeout=15,
        )
        assert check.returncode == 0, path

    _check(_migrate(project, 23, env=env))
    assert (project / VERSION).read_text() == "23\n"
    assert (project / POLICY).read_text() == (
        REPO / "templates/recovery/recovery-policy.yaml"
    ).read_text()
    too_early = _migrate(project, 22, inverse=True, env=env)
    assert too_early.returncode == 1 and "inverses of migrations above" in too_early.stderr
    assert (project / VERSION).read_text() == "23\n"

    historic_spec.write_text("An unrelated change after migration\n")
    _check(_migrate(project, 23, inverse=True, env=env))
    assert (project / VERSION).read_text() == "22\n"
    assert not (project / POLICY).exists()
    _check(_migrate(project, 22, inverse=True, env=env))
    assert (project / VERSION).read_text() == "21\n"
    assert gitignore.read_bytes() == b".local"
    assert historic_spec.read_text() == "An unrelated change after migration\n"
    assert not store_of(project, 22).parent.exists()


def test_format_23_preserves_the_original_policy_and_preimage_on_retry(tmp_path: Path) -> None:
    project = _project(tmp_path / "project", 22)
    policy = project / POLICY
    policy.write_bytes(b"# Keep my policy\nschema: 1\nstop_rules: original\n")
    _check(_migrate(project, 23))
    assert b"stop_rules: original" in policy.read_bytes()
    manifest, _ = _read_manifest(project, 23)
    before = manifest.read_bytes()
    policy.write_bytes(b"new bytes\n")
    _check(_migrate(project, 23))
    assert policy.read_bytes() == b"new bytes\n"
    assert manifest.read_bytes() == before
    _check(_migrate(project, 23, inverse=True))
    assert policy.read_bytes() == b"# Keep my policy\nschema: 1\nstop_rules: original\n"
    assert (project / VERSION).read_text() == "22\n"
    assert not (project / ".gitignore").exists()


def test_private_schema_1_scope_restores_modes_and_links(tmp_path: Path) -> None:
    project = _project(tmp_path / "project", 21)
    archived = project / ".specs/old"
    archived.mkdir()
    protected = archived / "links"
    protected.symlink_to(tmp_path / "external")
    external = tmp_path / "external"
    external.write_text("untouched")
    archived.chmod(0o555)
    assert record(project, 22, V22_LEGACY_SCOPE).status == "recorded"
    archived.chmod(0o755)
    protected.unlink()
    (archived / "added").write_text("generated")
    (project / VERSION).write_text("22\n")
    _check(_migrate(project, 22, inverse=True))
    assert (project / VERSION).read_text() == "21\n"
    assert protected.is_symlink() and protected.readlink() == external
    mode = archived.stat().st_mode & 0o777
    archived.chmod(0o755)  # Leave the fixture removable after observing the restored mode.
    assert mode == 0o555
    assert not (archived / "added").exists()
    assert external.read_text() == "untouched"


def test_retry_refuses_writes_not_covered_by_the_first_restore_point(tmp_path: Path) -> None:
    project = _project(tmp_path / "project", 21)
    record(project, 22, V22_LEGACY_SCOPE)
    manifest, _ = _read_manifest(project, 22)
    before = manifest.read_bytes()
    with pytest.raises(RestorePointError, match="first restore point does not cover"):
        record(project, 22, V22_SCOPE)
    assert manifest.read_bytes() == before
    assert not (project / ".gitignore").exists()


@pytest.mark.parametrize(
    ("corruption", "error"),
    [
        ("path", "unsafe relative"),
        ("in-repo", "restore scope does not match migration"),
        ("parent", "outside scope or out of order"),
        ("blob", "missing or altered"),
    ],
)
def test_invalid_manifest_is_refused_before_project_mutation(
    tmp_path: Path, corruption: str, error: str
) -> None:
    project = _project(tmp_path / "project", 21)
    sentinel = project / ".specs/sentinel"
    sentinel.write_text("before\n")
    record(project, 22, V22_LEGACY_SCOPE)
    manifest, document = _read_manifest(project, 22)
    if corruption == "path":
        document["scope"] = ["../outside"]
    elif corruption == "in-repo":
        document["scope"] = [*V22_LEGACY_SCOPE, "src"]
        source = project / "src/keep.py"
        source.parent.mkdir()
        source.write_text("# Cannot be deleted by a forged migration scope.\n")
    elif corruption == "parent":
        # Keep every original digest valid, but insert a write beneath an absent parent.
        entries = document["entries"]
        assert isinstance(entries, list)
        entries += [
            {
                "path": ".specs/foreign/sentinel",
                "kind": "file",
                "mode": 0o644,
                "digest": hashlib.sha256(b"before\n").hexdigest(),
                "target": None,
            }
        ]
    else:
        digest = hashlib.sha256(b"before\n").hexdigest()
        (manifest.parent / "blobs" / digest).write_text("tampered\n")
    manifest.write_text(json.dumps(document))
    sentinel.write_text("after\n")
    (project / VERSION).write_text("22\n")
    with pytest.raises(RestorePointError, match=error):
        restore(project, 22)
    assert (project / VERSION).read_text() == "22\n"
    assert sentinel.read_text() == "after\n"
    if corruption == "in-repo":
        assert (project / "src/keep.py").is_file()


def test_linked_restore_store_and_migration_destinations_are_refused(tmp_path: Path) -> None:
    project = _project(tmp_path / "project", 22)
    external = tmp_path / "external"
    external.mkdir()
    store = store_of(project, 23).parent
    store.symlink_to(external, target_is_directory=True)
    error = _migrate(project, 23)
    assert error.returncode == 1 and "must be a real directory" in error.stderr
    assert not list(external.iterdir())
    store.unlink()

    outside = external / "ignore"
    outside.write_text("keep outside\n")
    (project / ".gitignore").symlink_to(outside)
    error = _migrate(project, 23)
    assert error.returncode == 1 and "linked migration destination" in error.stderr
    assert not store.exists()
    assert outside.read_text() == "keep outside\n"
    assert (project / VERSION).read_text() == "22\n"


def test_store_is_git_ignored_before_the_root_exclusion_is_repaired(tmp_path: Path) -> None:
    project = _project(tmp_path / "project", 22)
    subprocess.run(["git", "init", "-q", str(project)], check=True, timeout=15)
    root_ignore = project / ".gitignore"
    previous = b"/.specs/.migration-restore/\n!/.specs/.migration-restore/\n"
    root_ignore.write_bytes(previous)
    record(project, 23, V23_SCOPE)
    untracked = subprocess.check_output(
        ["git", "-C", str(project), "ls-files", "--others", "--exclude-standard"],
        text=True,
        timeout=15,
    )
    assert ".specs/.migration-restore" not in untracked
    assert root_ignore.read_bytes() == previous
    _check(_migrate(project, 23))
    assert root_ignore.read_text().splitlines()[-1] == "/.specs/.migration-restore/"
    _check(_migrate(project, 23, inverse=True))
    assert root_ignore.read_bytes() == previous
    assert not store_of(project, 23).parent.exists()


def test_legacy_rollback_keeps_read_only_specs_and_user_ignore_file(tmp_path: Path) -> None:
    project = _project(tmp_path / "project", 21)
    specs = project / ".specs"
    point = store_of(project, 22)
    point.parent.mkdir()
    specs.chmod(0o555)
    try:
        record(project, 22, V22_LEGACY_SCOPE)
        specs.chmod(0o755)
        (project / VERSION).write_text("22\n")
        custom = point.parent / ".gitignore"
        custom.write_text("# My local rules\n/*\n")
        _check(_migrate(project, 22, inverse=True))
        assert (project / VERSION).read_text() == "21\n"
        assert specs.stat().st_mode & 0o777 == 0o555
        assert not point.exists()
        assert custom.read_text() == "# My local rules\n/*\n"
    finally:
        specs.chmod(0o755)


def test_mode_restore_failure_keeps_the_only_preimage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = _project(tmp_path / "project", 21)
    specs = project / ".specs"
    point = store_of(project, 22)
    point.parent.mkdir()
    specs.chmod(0o555)
    record(project, 22, V22_LEGACY_SCOPE)
    specs.chmod(0o755)
    (project / VERSION).write_text("22\n")
    original = Path.chmod

    def chmod(path: Path, mode: int, *, follow_symlinks: bool = True) -> None:
        if path == specs and mode == 0o555:
            raise PermissionError("cannot restore recorded mode")
        original(path, mode, follow_symlinks=follow_symlinks)

    monkeypatch.setattr(Path, "chmod", chmod)
    with pytest.raises(PermissionError, match="cannot restore recorded mode"):
        restore(project, 22)
    assert (point / "manifest.json").is_file()
    assert any((point / "blobs").iterdir())
    monkeypatch.undo()
    assert restore(project, 22).status == "restored"
    assert not point.exists()
    specs.chmod(0o755)
