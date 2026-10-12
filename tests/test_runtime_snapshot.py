"""Feature 083 install tests: immutable snapshots from committed trees (AC-001..AC-003)."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest
from typer.testing import CliRunner

from tests.runtime_support import (
    commit_all,
    git,
    install,
    make_source,
    restore_write_bits,
    tree_hashes,
    write,
)
from validator.cli import app
from validator.runtime import snapshot as snapshot_module
from validator.runtime.errors import RuntimeSnapshotError, RuntimeSourceError
from validator.runtime.home import RuntimeHome
from validator.runtime.manifest import read_manifest
from validator.runtime.models import MANIFEST_NAME, manifest_from_dict


def independent_digest(root: Path) -> str:
    """Recompute a snapshot digest without the production walker (spec Definitions)."""
    records: list[tuple[str, str]] = []
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root).as_posix()
        if rel == MANIFEST_NAME or (path.is_dir() and not path.is_symlink()):
            continue
        if path.is_symlink():
            kind, flag, payload = "symlink", "0", os.readlink(path).encode()
        else:
            executable = bool(path.stat().st_mode & stat.S_IXUSR)
            kind, flag, payload = "file", "1" if executable else "0", path.read_bytes()
        records.append((rel, f"{kind}\0{flag}\0{rel}\0{hashlib.sha256(payload).hexdigest()}\n"))
    digest = hashlib.sha256("".join(line for _rel, line in sorted(records)).encode())
    return f"sha256:{digest.hexdigest()}"


@pytest.fixture
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[RuntimeHome]:
    """Temporary runtime home; HOME is redirected and write bits restored on teardown."""
    monkeypatch.setenv("HOME", str(tmp_path / "user-home"))
    root = (tmp_path / "runtime-home").resolve()
    monkeypatch.setenv("LIVESPEC_HOME", str(root))
    yield RuntimeHome(root)
    restore_write_bits(tmp_path)


@pytest.fixture
def source(tmp_path: Path) -> Path:
    """Clean temporary LiveSpec git source with VERSION 21."""
    return make_source(tmp_path / "livespec-src")


def _cli(monkeypatch: pytest.MonkeyPatch, *args: str) -> tuple[int, str, str]:
    monkeypatch.setattr(sys, "argv", ["livespec", *args])
    result = CliRunner().invoke(app, list(args))
    return result.exit_code, result.stdout, result.stderr


def test_clean_head_installs_read_only_snapshot(
    home: RuntimeHome, source: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC-001: committed tree minus .specs/tests, manifest, digest, read-only, current, shim."""
    code, out, _err = _cli(
        monkeypatch,
        "runtime",
        "install",
        "--source",
        str(source),
        "--home",
        str(home.root),
        "--json",
    )
    assert code == 0
    payload = json.loads(out)
    commit = git(source, "rev-parse", "HEAD").strip()
    assert payload["status"] == "created" and payload["runtime_id"] == f"21-{commit[:12]}"
    snapshot = home.snapshot(payload["runtime_id"])
    tracked = git(source, "ls-tree", "-r", "--name-only", "HEAD").split()
    expected = {path for path in tracked if path.split("/")[0] not in {".specs", "tests"}}
    assert set(tree_hashes(snapshot)) - {MANIFEST_NAME} == expected
    manifest = json.loads((snapshot / MANIFEST_NAME).read_text())
    assert manifest["schema"] == 1 and manifest["commit"] == commit
    assert manifest["runtime_id"] == payload["runtime_id"] == snapshot.name
    assert manifest["livespec_version"] == 21 and manifest["source"] == str(source.resolve())
    assert manifest["created_at"].endswith("Z")
    assert manifest["content_digest"] == independent_digest(snapshot)
    for path in [snapshot, *snapshot.rglob("*")]:
        if not path.is_symlink():
            assert path.lstat().st_mode & 0o222 == 0, path
    assert home.current.resolve() == snapshot.resolve()
    assert os.access(home.shim, os.X_OK)
    assert (snapshot / "scripts/run.sh").stat().st_mode & stat.S_IXUSR
    assert os.readlink(snapshot / "docs/version-link") == "../VERSION"


@pytest.mark.parametrize(
    "dirty_path",
    ["VERSION", "untracked.txt", ".specs/new.md", "tests/new_test.py"],
)
def test_dirty_default_ref_is_refused(home: RuntimeHome, source: Path, dirty_path: str) -> None:
    """AC-002: any tracked change or untracked file, even in excluded dirs, blocks HEAD."""
    write(source / dirty_path, "changed\n")
    with pytest.raises(RuntimeSourceError) as caught:
        install(home, source)
    assert dirty_path in caught.value.message
    assert not home.root.exists()


def test_explicit_ref_snapshots_committed_bytes_only(home: RuntimeHome, source: Path) -> None:
    """AC-002: --ref on a dirty tree takes the commit's bytes, none of the changes."""
    commit = git(source, "rev-parse", "HEAD").strip()
    write(source / "VERSION", "99\n")
    write(source / "untracked.txt", "dirty\n")
    result = install(home, source, ref=commit)
    assert (result.snapshot / "VERSION").read_text() == "21\n"
    assert not (result.snapshot / "untracked.txt").exists()
    branch = git(source, "rev-parse", "--abbrev-ref", "HEAD").strip()
    assert install(home, source, ref=branch).status == "reused"


def test_invalid_source_or_ref_writes_nothing(
    home: RuntimeHome, source: Path, tmp_path: Path
) -> None:
    """AC-002: non-git LiveSpec root, non-LiveSpec repo and unknown ref exit with no write."""
    not_git = tmp_path / "not-git"
    write(not_git / "VERSION", "21\n")
    (not_git / "validator").mkdir()
    (not_git / ".agent-sync").mkdir()
    plain_repo = tmp_path / "plain"
    write(plain_repo / "README.md", "x\n")
    git(plain_repo, "init", "-q")
    for bad_source in (not_git, plain_repo):
        with pytest.raises(RuntimeSourceError):
            install(home, bad_source)
    with pytest.raises(RuntimeSourceError, match="no-such-ref"):
        install(home, source, ref="no-such-ref")
    assert not home.root.exists()


def test_reuse_no_activate_and_corruption(home: RuntimeHome, source: Path) -> None:
    """AC-003: reuse keeps bytes, --no-activate keeps current, corruption is refused."""
    first = install(home, source)
    write(source / "README.md", "second\n")
    commit_all(source, "second")
    second = install(home, source, activate=False)
    assert home.current.resolve() == first.snapshot.resolve()
    before = tree_hashes(second.snapshot)
    again = install(home, source, activate=False)
    assert again.status == "reused" and tree_hashes(second.snapshot) == before
    assert home.current.resolve() == first.snapshot.resolve() and home.shim.is_file()
    target = second.snapshot / "README.md"
    target.chmod(0o644)
    target.write_text("tampered\n")
    target.chmod(0o444)
    corrupted = tree_hashes(second.snapshot)
    with pytest.raises(RuntimeSnapshotError, match=second.runtime_id):
        install(home, source)
    assert tree_hashes(second.snapshot) == corrupted
    assert home.current.resolve() == first.snapshot.resolve()


def test_missing_manifest_is_refused(home: RuntimeHome, source: Path) -> None:
    """AC-003: an existing directory without a valid manifest is never overwritten."""
    result = install(home, source)
    result.snapshot.chmod(0o755)
    (result.snapshot / MANIFEST_NAME).unlink()
    with pytest.raises(RuntimeSnapshotError):
        install(home, source)
    assert not (result.snapshot / MANIFEST_NAME).exists()


@pytest.mark.parametrize("field", ["runtime_id", "commit"])
def test_mismatched_manifest_identity_is_refused(
    home: RuntimeHome, source: Path, field: str
) -> None:
    """AC-003: a manifest whose runtime id or commit differs is refused; digest still matches."""
    result = install(home, source)
    manifest_path = result.snapshot / MANIFEST_NAME
    manifest = json.loads(manifest_path.read_text())
    manifest[field] = manifest[field][:-4] + "ffff"
    result.snapshot.chmod(0o755)
    manifest_path.chmod(0o644)
    manifest_path.write_text(json.dumps(manifest))
    before = tree_hashes(result.snapshot)
    with pytest.raises(RuntimeSnapshotError) as caught:
        install(home, source, activate=False)
    assert result.runtime_id in caught.value.message or "differs" in caught.value.message
    assert tree_hashes(result.snapshot) == before


def test_interrupted_install_and_stale_staging(
    home: RuntimeHome, source: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC-003: no partial final dir; the next install removes dead staging dirs."""

    def interrupt(*_args: object) -> str:
        """Simulate a signal arriving after staging was written."""
        raise KeyboardInterrupt

    monkeypatch.setattr(snapshot_module, "_seal_and_publish", interrupt)
    with pytest.raises(KeyboardInterrupt):
        install(home, source)
    assert [path.name for path in home.versions.iterdir()] == []
    monkeypatch.undo()
    monkeypatch.setenv("LIVESPEC_HOME", str(home.root))
    stale = home.versions / ".staging-21-aaaaaaaaaaaa-999999-dead"
    write(stale / "sub/file.txt", "left over\n")
    (stale / "sub").chmod(0o555)
    stale.chmod(0o555)
    result = install(home, source)
    assert not stale.exists() and result.status == "created"
    assert [path.name for path in home.versions.iterdir()] == [result.runtime_id]


def test_lost_rename_race_reuses_winner(home: RuntimeHome, source: Path) -> None:
    """Edge case: a concurrent install that loses the rename reuses the verified winner."""
    result = install(home, source)
    base = read_manifest(result.snapshot)
    entries = snapshot_module.list_snapshot_entries(source.resolve(), base.commit)
    blobs = snapshot_module.read_blobs(source.resolve(), [entry.oid for entry in entries])
    status = snapshot_module._build_snapshot(home, base, entries, blobs)
    assert status == "reused"
    assert [path.name for path in home.versions.iterdir()] == [result.runtime_id]


def test_unsafe_committed_trees_are_refused(home: RuntimeHome, source: Path) -> None:
    """D-01 and edge cases: escaping symlinks, gitlinks and a non-integer VERSION."""
    os.symlink("/etc/hosts", source / "absolute-link")
    commit_all(source, "absolute link")
    with pytest.raises(RuntimeSourceError, match="absolute-link"):
        install(home, source)
    (source / "absolute-link").unlink()
    os.symlink("../../outside", source / "docs/escape")
    commit_all(source, "escaping link")
    with pytest.raises(RuntimeSourceError, match="docs/escape"):
        install(home, source)
    (source / "docs/escape").unlink()
    write(source / "VERSION", "not-a-number\n")
    commit = commit_all(source, "bad version")
    with pytest.raises(RuntimeSourceError, match=commit):
        install(home, source)
    head = git(source, "rev-parse", "HEAD").strip()
    git(source, "update-index", "--add", "--cacheinfo", f"160000,{head},vendor/sub")
    git(source, "commit", "-q", "-m", "gitlink")
    with pytest.raises(RuntimeSourceError, match="vendor/sub"):
        install(home, source)
    assert not home.root.exists()


def test_staging_named_symlink_is_unlinked_without_following(
    home: RuntimeHome, source: Path, tmp_path: Path
) -> None:
    """Audit #13: a staging-named symlink is removed itself; its outside target is untouched."""
    outside = tmp_path / "outside"
    kept = write(outside / "keep.txt", "keep\n", mode=0o444)
    outside.chmod(0o555)
    home.versions.mkdir(parents=True)
    link = home.versions / ".staging-21-aaaaaaaaaaaa-999999-link"
    os.symlink(outside, link)
    modes = (outside.stat().st_mode, kept.stat().st_mode)
    result = install(home, source)
    assert not link.is_symlink() and result.status == "created"
    assert (outside.stat().st_mode, kept.stat().st_mode, kept.read_text()) == (*modes, "keep\n")


@pytest.mark.parametrize("relative", ["VERSION", "."], ids=["file", "root"])
def test_writable_snapshot_is_refused(home: RuntimeHome, source: Path, relative: str) -> None:
    """Audit #10: a chmod-only change (write bit regained) fails verification."""
    result = install(home, source)
    (result.snapshot / relative).chmod(0o755 if relative == "." else 0o644)
    before = tree_hashes(result.snapshot)
    with pytest.raises(RuntimeSnapshotError, match="read-only"):
        install(home, source, activate=False)
    assert tree_hashes(result.snapshot) == before


VALID_MANIFEST: dict[str, object] = {
    "schema": 1,
    "runtime_id": "21-0123456789ab",
    "livespec_version": 21,
    "commit": "0123456789ab" + "c" * 28,
    "source": "/srv/livespec",
    "created_at": "2026-10-11T12:00:00Z",
    "content_digest": "sha256:" + "d" * 64,
}


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("schema", True),
        ("schema", "1"),
        ("runtime_id", "21-NOTHEX"),
        ("runtime_id", "22-0123456789ab"),
        ("commit", "0123456789ab"),
        ("content_digest", "sha256:abc"),
        ("content_digest", "d" * 64),
        ("created_at", "2026-10-11T12:00:00"),
        ("created_at", "2026-10-11T12:00:00+02:00"),
        ("created_at", "yesterday"),
        ("source", "relative/path"),
    ],
)
def test_manifest_schema_is_strict(tmp_path: Path, field: str, value: object) -> None:
    """Audit #9: types, formats, id/version/commit relation, digest and UTC timestamp."""
    assert manifest_from_dict(dict(VALID_MANIFEST), tmp_path).runtime_id == "21-0123456789ab"
    invalid = {**VALID_MANIFEST, field: value}
    with pytest.raises(RuntimeSnapshotError, match="invalid runtime manifest"):
        manifest_from_dict(invalid, tmp_path)


def test_remove_tree_requires_a_real_direct_child(tmp_path: Path) -> None:
    """Audit round 2 #8: deletion refuses symlinks and paths outside the container."""
    from validator.runtime.errors import LiveSpecRuntimeError

    container = tmp_path / "versions"
    outside = tmp_path / "outside"
    (outside / "keep").mkdir(parents=True)
    (container / "nested" / "deeper").mkdir(parents=True)
    os.symlink(outside, container / "link")
    with pytest.raises(LiveSpecRuntimeError, match="symlink"):
        snapshot_module.remove_tree(container / "link", container)
    with pytest.raises(LiveSpecRuntimeError, match="outside"):
        snapshot_module.remove_tree(outside, container)
    with pytest.raises(LiveSpecRuntimeError, match="outside"):
        snapshot_module.remove_tree(container / "nested" / "deeper", container)
    assert (outside / "keep").is_dir() and (container / "nested" / "deeper").is_dir()
    snapshot_module.remove_tree(container / "nested", container)
    assert not (container / "nested").exists()


def test_remove_tree_refuses_a_regular_file_child(tmp_path: Path) -> None:
    """Audit round 3 #5: a direct-child regular file is refused with the runtime error."""
    from validator.runtime.errors import LiveSpecRuntimeError

    container = tmp_path / "versions"
    container.mkdir()
    (container / "file.txt").write_text("keep\n")
    with pytest.raises(LiveSpecRuntimeError, match="non-directory"):
        snapshot_module.remove_tree(container / "file.txt", container)
    assert (container / "file.txt").read_text() == "keep\n"
