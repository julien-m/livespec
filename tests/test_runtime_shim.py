"""Feature 083 shim tests: lock-driven runtime resolution and exit 3 (AC-004, AC-005, SC-003)."""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
from collections.abc import Iterator
from pathlib import Path
from typing import NamedTuple

import pytest

from tests.runtime_support import (
    PYTHON,
    commit_all,
    install,
    make_project,
    make_source,
    make_stub_checkout,
    restore_write_bits,
    run_shim,
    write,
)
from validator.runtime import shim_core
from validator.runtime.errors import LiveSpecRuntimeError
from validator.runtime.home import RuntimeHome
from validator.runtime.manifest import read_manifest
from validator.runtime.project import lock_bytes
from validator.runtime.shim import SHIM_CORE_PATH, write_shim
from validator.runtime.shim_core import LockData


class Installed(NamedTuple):
    """Module fixture: a real-code source with two installed runtimes (B is current)."""

    base: Path
    source: Path
    home: RuntimeHome
    runtime_a: str
    runtime_b: str


@pytest.fixture(scope="module")
def installed(tmp_path_factory: pytest.TempPathFactory) -> Iterator[Installed]:
    """Install two snapshots of a real-code source into a temporary home."""
    base = tmp_path_factory.mktemp("shim").resolve()
    source = make_source(base / "livespec-src", real_code=True)
    home = RuntimeHome(base / "home")
    first = install(home, source)
    write(source / "README.md", "second\n")
    commit_all(source, "second")
    second = install(home, source)
    yield Installed(base, source, home, first.runtime_id, second.runtime_id)
    restore_write_bits(base)


def _env(installed: Installed) -> dict[str, str]:
    env = {key: value for key, value in os.environ.items() if key != "LIVESPEC_HOME"}
    env["HOME"] = str(installed.base / "user-home")
    return env


def _pin_lock(project: Path, home: RuntimeHome, runtime_id: str) -> Path:
    manifest = read_manifest(home.snapshot(runtime_id))
    lock: LockData = {
        "schema": 1,
        "mode": "pinned",
        "runtime_id": runtime_id,
        "livespec_version": manifest.livespec_version,
        "commit": manifest.commit,
    }
    write(project / ".specs/.livespec-path", f"{home.snapshot(runtime_id).resolve()}\n")
    return write(project / ".specs/livespec.lock", lock_bytes(lock).decode())


def test_pinned_lock_runs_its_snapshot_from_nested_directory(
    installed: Installed, tmp_path: Path
) -> None:
    """AC-004: the pinned snapshot executes even with an editable checkout installed."""
    project = make_project(tmp_path / "project")
    _pin_lock(project, installed.home, installed.runtime_a)
    nested = project / "src" / "deep"
    nested.mkdir(parents=True)
    result = run_shim(installed.home, nested, "runtime", "status", "--json", env=_env(installed))
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    snapshot = installed.home.snapshot(installed.runtime_a).resolve()
    assert payload["executing_root"] == str(snapshot)
    assert payload["executing_validator"] == str(snapshot / "validator")
    assert payload["resolved_root"] == str(snapshot) and payload["findings"] == []
    editable = subprocess.run(
        [PYTHON, "-c", "import validator; print(validator.__file__)"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert editable.returncode == 0 and editable.stdout.strip().endswith("__init__.py")
    assert str(snapshot) not in editable.stdout


def test_dev_lock_passes_args_stdin_exit_and_home(installed: Installed, tmp_path: Path) -> None:
    """AC-004/AC-005: relative dev source from the project root, unchanged args/stdin/exit."""
    checkout = make_stub_checkout(tmp_path / "livespec-dev")
    project = make_project(tmp_path / "project")
    write(
        project / ".specs/livespec.lock",
        '{"mode": "dev", "schema": 1, "source": "../livespec-dev"}\n',
    )
    nested = project / "pkg" / "sub"
    nested.mkdir(parents=True)
    result = run_shim(
        installed.home, nested, "alpha", "--beta", "x y", stdin="hello\n", env=_env(installed)
    )
    assert result.returncode == 7
    payload = json.loads(result.stdout)
    assert payload["argv"] == ["alpha", "--beta", "x y"] and payload["stdin"] == "hello\n"
    assert payload["home"] == str(installed.home.root)
    assert payload["file"].startswith(str(checkout.resolve()))
    assert result.stderr.startswith(shim_core.NOTICE_PREFIX)


def test_missing_pinned_snapshot_exits_3_then_runtime_falls_back(
    installed: Installed, tmp_path: Path
) -> None:
    """AC-005/AC-015/AC-016: exit 3 with recovery; runtime subcommands use current."""
    project = make_project(tmp_path / "project")
    commit = "b" * 40
    lock = {"schema": 1, "mode": "pinned", "runtime_id": "21-bbbbbbbbbbbb"}
    lock.update({"livespec_version": 21, "commit": commit})
    write(project / ".specs/livespec.lock", json.dumps(lock))
    env = _env(installed)
    refused = run_shim(installed.home, project, "status", env=env)
    assert refused.returncode == 3 and refused.stdout == ""
    assert refused.stderr.startswith("livespec-shim:") and "21-bbbbbbbbbbbb" in refused.stderr
    assert f"livespec runtime install --source <livespec repo> --ref {commit}" in refused.stderr
    status = run_shim(installed.home, project, "runtime", "status", "--json", env=env)
    assert status.returncode == 1 and shim_core.WARNING_PREFIX in status.stderr
    codes = {item["code"] for item in json.loads(status.stdout)["findings"]}
    assert {"runtime_snapshot_missing", "runtime_executing_mismatch"} <= codes
    commit_a = read_manifest(installed.home.snapshot(installed.runtime_a)).commit
    args = ["runtime", "install", "--source", str(installed.source), "--ref", commit_a]
    args += ["--no-activate", "--json"]
    recovered = run_shim(installed.home, project, *args, env=env)
    assert recovered.returncode == 0 and shim_core.WARNING_PREFIX in recovered.stderr
    assert json.loads(recovered.stdout)["status"] == "reused"


def test_manifest_commit_differing_from_lock_exits_3(installed: Installed, tmp_path: Path) -> None:
    """AC-005: an installed snapshot whose manifest commit differs from the lock is refused."""
    project = make_project(tmp_path / "project")
    manifest = read_manifest(installed.home.snapshot(installed.runtime_a))
    forged = manifest.commit[:12] + "0" * (len(manifest.commit) - 12)
    lock: LockData = {
        "schema": 1,
        "mode": "pinned",
        "runtime_id": installed.runtime_a,
        "livespec_version": manifest.livespec_version,
        "commit": forged,
    }
    write(project / ".specs/livespec.lock", lock_bytes(lock).decode())
    refused = run_shim(installed.home, project, "status", env=_env(installed))
    assert refused.returncode == 3 and refused.stdout == ""
    assert installed.runtime_a in refused.stderr and f"--ref {forged}" in refused.stderr


@pytest.mark.parametrize(
    "lock_text",
    ["not json", '{"schema": 2, "mode": "dev", "source": "."}', '{"schema": 1, "mode": "odd"}'],
    ids=["not-json", "unknown-schema", "unknown-mode"],
)
def test_invalid_lock_exits_3_except_runtime_subcommands(
    installed: Installed, tmp_path: Path, lock_text: str
) -> None:
    """AC-005: invalid locks never fall back for normal commands; status reports ERROR."""
    project = make_project(tmp_path / "project")
    lock = write(project / ".specs/livespec.lock", lock_text)
    refused = run_shim(installed.home, project, "status", env=_env(installed))
    assert refused.returncode == 3 and refused.stdout == ""
    assert refused.stderr.startswith("livespec-shim:") and str(lock.resolve()) in refused.stderr
    status = run_shim(installed.home, project, "runtime", "status", "--json", env=_env(installed))
    assert status.returncode == 1 and shim_core.WARNING_PREFIX in status.stderr
    findings = json.loads(status.stdout)["findings"]
    assert [(item["code"], item["severity"]) for item in findings] == [
        ("runtime_lock_invalid", "ERROR")
    ]


def test_nested_project_without_lock_ignores_parent_lock(
    installed: Installed, tmp_path: Path
) -> None:
    """AC-004: resolution stops at the project root; the unlocked child runs current."""
    parent = make_project(tmp_path / "parent")
    write(parent / ".specs/livespec.lock", "not json")
    child = make_project(parent / "packages" / "child")
    result = run_shim(installed.home, child, "runtime", "status", "--json", env=_env(installed))
    assert result.returncode == 0 and result.stderr == ""
    payload = json.loads(result.stdout)
    assert payload["mode"] == "unpinned"
    assert payload["executing_root"] == str(installed.home.snapshot(installed.runtime_b).resolve())


def test_no_current_and_bad_dev_source_exit_3(installed: Installed, tmp_path: Path) -> None:
    """AC-005: no lock and no current names the checkout CLI; a non-root dev source fails."""
    empty = RuntimeHome((tmp_path / "empty-home").resolve())
    write_shim(empty, PYTHON)
    outside = tmp_path / "no-project"
    outside.mkdir()
    env = _env(installed)
    result = run_shim(empty, outside, "runtime", "status", env=env)
    assert result.returncode == 3 and "python3 -m validator.cli runtime install" in result.stderr
    project = make_project(tmp_path / "project")
    _pin_lock(project, installed.home, installed.runtime_a)
    pinned = run_shim(empty, project, "status", env=env)
    assert pinned.returncode == 3 and "python3 -m validator.cli runtime install" in pinned.stderr
    write(project / ".specs/livespec.lock", '{"mode": "dev", "schema": 1, "source": "missing"}')
    dev = run_shim(installed.home, project, "status", env=env)
    assert dev.returncode == 3 and "not a LiveSpec root" in dev.stderr


def test_generated_home_reaches_executed_runtime(installed: Installed, tmp_path: Path) -> None:
    """AC-005: without LIVESPEC_HOME the runtime resolves current from the shim's home."""
    project = make_project(tmp_path / "project")
    args = ["runtime", "pin", "--project", str(project), "--json"]
    result = run_shim(installed.home, project, *args, env=_env(installed))
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["lock"]["runtime_id"] == installed.runtime_b


def test_resolution_reads_only_lock_and_one_manifest(
    installed: Installed, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """SC-003: one lock and one manifest per invocation, never a digest computation."""
    project = make_project(tmp_path / "project")
    lock = _pin_lock(project, installed.home, installed.runtime_a)
    reads: list[Path] = []
    original = pathlib.Path.read_text

    def recording(self: Path, encoding: str | None = None, errors: str | None = None) -> str:
        """Record the path, then delegate to the real reader."""
        reads.append(self)
        return original(self, encoding=encoding, errors=errors)

    monkeypatch.setattr(pathlib.Path, "read_text", recording)
    resolution = shim_core.resolve_runtime(project, installed.home.root, ["status"])
    manifest = installed.home.snapshot(installed.runtime_a) / shim_core.MANIFEST_FILE
    assert reads == [lock.resolve(), manifest]
    assert resolution.root == installed.home.snapshot(installed.runtime_a)
    source = SHIM_CORE_PATH.read_text(encoding="utf-8")
    assert "hashlib" not in source and "compute_digest" not in source


def test_generated_shim_embeds_core_and_refuses_whitespace(
    installed: Installed, tmp_path: Path
) -> None:
    """D-06: shebang names the interpreter; the core is embedded verbatim, never imported."""
    text = installed.home.shim.read_text(encoding="utf-8")
    assert text.startswith(f"#!{PYTHON}\n")
    assert SHIM_CORE_PATH.read_text(encoding="utf-8") in text
    assert f"GENERATED_HOME = {str(installed.home.root)!r}" in text
    assert "import validator" not in text
    with pytest.raises(LiveSpecRuntimeError, match="whitespace"):
        write_shim(RuntimeHome(tmp_path / "with space"), PYTHON)


def test_manifest_runtime_id_differing_from_lock_exits_3(
    installed: Installed, tmp_path: Path
) -> None:
    """AC-005: an installed manifest whose runtime_id differs from the lock is refused."""
    home = RuntimeHome((tmp_path / "forged-home").resolve())
    write_shim(home, PYTHON)
    manifest_path = installed.home.snapshot(installed.runtime_a) / shim_core.MANIFEST_FILE
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    commit = manifest["commit"]
    manifest["runtime_id"] = installed.runtime_b
    write(home.snapshot(installed.runtime_a) / shim_core.MANIFEST_FILE, json.dumps(manifest))
    project = make_project(tmp_path / "project")
    lock: LockData = {
        "schema": 1,
        "mode": "pinned",
        "runtime_id": installed.runtime_a,
        "livespec_version": manifest["livespec_version"],
        "commit": commit,
    }
    write(project / ".specs/livespec.lock", lock_bytes(lock).decode())
    refused = run_shim(home, project, "status", env=_env(installed))
    assert refused.returncode == 3 and refused.stdout == ""
    assert refused.stderr.startswith("livespec-shim:") and installed.runtime_a in refused.stderr
    assert f"livespec runtime install --source <livespec repo> --ref {commit}" in refused.stderr


def _fake_snapshot(home: RuntimeHome, name: str, manifest: dict[str, object]) -> Path:
    root = home.snapshot(name)
    write(root / "VERSION", "21\n")
    (root / ".agent-sync").mkdir()
    write(root / "validator/__init__.py", '"""Fake runtime package."""\n')
    write(root / ".livespec-runtime.json", json.dumps(manifest))
    return root


@pytest.mark.parametrize("target", ["checkout", "mismatched-manifest"])
def test_current_must_be_a_verified_snapshot(
    installed: Installed, tmp_path: Path, target: str
) -> None:
    """Audit #15: current pointing at a checkout or a mismatched manifest is refused (exit 3)."""
    home = RuntimeHome((tmp_path / "fake-home").resolve())
    write_shim(home, PYTHON)
    if target == "checkout":
        destination = make_stub_checkout(tmp_path / "checkout")
    else:
        identity = {"runtime_id": "21-bbbbbbbbbbbb", "livespec_version": 21, "commit": "b" * 40}
        destination = _fake_snapshot(home, "21-aaaaaaaaaaaa", identity)
    os.symlink(destination, home.current)
    outside = tmp_path / "no-project"
    outside.mkdir()
    for args in (["status"], ["runtime", "status"]):
        result = run_shim(home, outside, *args, env=_env(installed))
        assert result.returncode == 3 and result.stdout == "", args
        assert "does not point to an installed runtime snapshot" in result.stderr


def test_current_with_incomplete_manifest_exits_3(installed: Installed, tmp_path: Path) -> None:
    """Audit round 2 #6: a matching identity in an incomplete manifest is not a snapshot."""
    home = RuntimeHome((tmp_path / "fake-home").resolve())
    write_shim(home, PYTHON)
    identity = {"runtime_id": "21-aaaaaaaaaaaa", "livespec_version": 21, "commit": "a" * 40}
    os.symlink(_fake_snapshot(home, "21-aaaaaaaaaaaa", identity), home.current)
    outside = tmp_path / "no-project"
    outside.mkdir()
    result = run_shim(home, outside, "status", env=_env(installed))
    assert result.returncode == 3 and result.stdout == ""
    assert "does not point to an installed runtime snapshot" in result.stderr


def test_looping_current_symlink_exits_3_without_traceback(
    installed: Installed, tmp_path: Path
) -> None:
    """Audit round 2 #7: a self-referential current is reported, never a traceback."""
    home = RuntimeHome((tmp_path / "fake-home").resolve())
    write_shim(home, PYTHON)
    os.symlink(home.current, home.current)
    outside = tmp_path / "no-project"
    outside.mkdir()
    for args in (["status"], ["runtime", "status"]):
        result = run_shim(home, outside, *args, env=_env(installed))
        assert result.returncode == 3, args
        assert result.stderr.startswith("livespec-shim:") and "Traceback" not in result.stderr


@pytest.mark.parametrize(
    ("source", "created_at"),
    [("relative/source", "2026-10-11T00:00:00+00:00"), ("/abs/source", "yesterday")],
)
def test_current_with_malformed_source_or_timestamp_exits_3(
    installed: Installed, tmp_path: Path, source: str, created_at: str
) -> None:
    """Audit round 3 #4: non-digest manifest fields are validated without recomputing it."""
    home = RuntimeHome((tmp_path / "fake-home").resolve())
    write_shim(home, PYTHON)
    manifest: dict[str, object] = {
        "schema": 1,
        "runtime_id": "21-aaaaaaaaaaaa",
        "livespec_version": 21,
        "commit": "a" * 40,
        "source": source,
        "created_at": created_at,
        "content_digest": "sha256:" + "0" * 64,
    }
    os.symlink(_fake_snapshot(home, "21-aaaaaaaaaaaa", manifest), home.current)
    outside = tmp_path / "no-project"
    outside.mkdir()
    result = run_shim(home, outside, "status", env=_env(installed))
    assert result.returncode == 3
    assert "does not point to an installed runtime snapshot" in result.stderr
