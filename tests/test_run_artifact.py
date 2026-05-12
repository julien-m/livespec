"""Tests for validator/run_artifact.py.

# @spec FR-005: RunArtifact schema — .specs/features/039-command-expectations-and-verify-output/spec.md#fr-005
# @spec EC-007: malformed artifact — .specs/features/039-command-expectations-and-verify-output/spec.md#ec-007
# @spec EC-009: lexicographic latest — .specs/features/039-command-expectations-and-verify-output/spec.md#ec-009
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from validator.exceptions import ArtifactMalformed
from validator.run_artifact import (
    FsChange,
    GitState,
    RunArtifact,
    find_latest_artifact,
    read_artifact,
    record_subprocess,
    rotate_artifacts,
    truncate_stream,
)


def _make_artifact(name: str = "demo", **kwargs) -> RunArtifact:
    return RunArtifact(
        command=name,
        timestamp=kwargs.get("timestamp", "2026-05-12T10:00:00Z"),
        flags=kwargs.get("flags", []),
        stdout=kwargs.get("stdout", "hello"),
        stderr=kwargs.get("stderr", ""),
        exit_code=kwargs.get("exit_code", 0),
        duration_ms=kwargs.get("duration_ms", 12),
        cwd=kwargs.get("cwd", "/tmp"),
        git_state_before=GitState(branch="main", head_sha="abc", dirty=[]),
        git_state_after=GitState(branch="main", head_sha="abc", dirty=["x"]),
        fs_observed=[FsChange(path="x", change="create")],
    )


def test_write_read_round_trip(tmp_path):
    art = _make_artifact()
    final = art.write(tmp_path / ".runs")
    loaded = read_artifact(final)
    assert loaded.command == art.command
    assert loaded.timestamp == art.timestamp
    assert loaded.exit_code == 0
    assert loaded.fs_observed[0].path == "x"
    assert loaded.git_state_after.dirty == ["x"]


def test_find_latest_artifact_picks_lex_last(tmp_path):
    runs = tmp_path / ".runs"
    _make_artifact(timestamp="2026-05-11T09:00:00Z").write(runs)
    latest = _make_artifact(timestamp="2026-05-12T10:00:00Z").write(runs)
    _make_artifact(timestamp="2026-05-12T08:00:00Z").write(runs)
    assert find_latest_artifact("demo", runs) == latest


def test_find_latest_returns_none_when_empty(tmp_path):
    assert find_latest_artifact("demo", tmp_path) is None


def test_rotation_archives_oldest(tmp_path):
    runs = tmp_path / ".runs"
    # Write 22 artifacts; rotation keep=20 -> 2 oldest archived.
    for i in range(22):
        ts = f"2026-05-12T{i:02d}-00-00Z"
        _make_artifact(timestamp=ts).write(runs)
    rotate_artifacts("demo", runs, keep=20)
    remaining = sorted(runs.glob("demo-*.json"))
    archived = sorted((runs / "_archive").glob("demo-*.json"))
    assert len(remaining) == 20
    assert len(archived) == 2


def test_malformed_artifact_raises_artifact_malformed_and_classifies_as_blocked(tmp_path):
    """EC-007: invalid JSON => ArtifactMalformed; verifier maps it to blocked."""
    bad = tmp_path / "demo-2026-05-12T10-00-00Z.json"
    bad.write_text("{not json", encoding="utf-8")
    with pytest.raises(ArtifactMalformed) as excinfo:
        read_artifact(bad)
    assert "JSONDecodeError" in str(excinfo.value)
    # The mapping to outcome=blocked is exercised in test_verify_output.py
    # (test_blocked_when_artifact_malformed). We assert the exception class here.


def test_artifact_missing_required_field_raises(tmp_path):
    bad = tmp_path / "demo.json"
    bad.write_text(json.dumps({"command": "demo"}), encoding="utf-8")
    with pytest.raises(ArtifactMalformed):
        read_artifact(bad)


def test_truncate_stream_appends_marker():
    big = "x" * 2_000_000
    out = truncate_stream(big, limit=1024)
    assert "[...truncated" in out
    assert len(out.encode("utf-8")) < 1024 + 100


def test_record_subprocess_writes_artifact(tmp_path):
    art = record_subprocess(
        "echo-demo",
        ["echo", "hello-world"],
        cwd=tmp_path,
        runs_dir=tmp_path / ".specs" / ".runs",
    )
    assert art.exit_code == 0
    assert "hello-world" in art.stdout
    path = find_latest_artifact("echo-demo", tmp_path / ".specs" / ".runs")
    assert path is not None
    assert path.exists()


def test_record_subprocess_captures_nonzero_exit(tmp_path):
    art = record_subprocess(
        "failing",
        ["sh", "-c", "echo boom; exit 3"],
        cwd=tmp_path,
        runs_dir=tmp_path / ".runs",
    )
    assert art.exit_code == 3
    assert "boom" in art.stdout
