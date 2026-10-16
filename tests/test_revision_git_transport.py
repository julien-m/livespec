"""Revision extraction avoids duplex pipes while preserving raw committed blobs."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

from tests.stable_review_support import FEATURE, commit_all, make_root
from validator.delivery.revision_commit import _blobs


def _large_root(tmp_path: Path) -> Path:
    root = make_root(tmp_path)
    archive = root / ".specs/archive"
    archive.mkdir()
    # A request spanning PIPE_BUF and several MiB of responses, like the blocked project.
    for index in range(141):
        (archive / f"{index}.bin").write_bytes(bytes([index]) * 32768)
    commit_all(root, "archived evidence")
    return root


# @spec AC-002: Opening verifies raw committed sources
#   — .specs/features/094-verified-review-continuity/spec.md#ac-002
def test_batch_extraction_does_not_require_a_duplex_pipe(tmp_path: Path) -> None:
    root = _large_root(tmp_path)
    original_run = subprocess.run
    with patch(
        "validator.delivery.revision_commit.subprocess.run",
        side_effect=lambda *args, **kwargs: original_run(*args, **(kwargs | {"timeout": 1})),
    ) as run:
        blobs = _blobs(root, "HEAD", [".specs/archive"])
    assert blobs is not None and len(blobs) == 141
    assert blobs[".specs/archive/140.bin"] == ("100644", bytes([140]) * 32768)
    batch = run.call_args
    assert batch is not None
    has_duplex_input = "input" in batch.kwargs
    assert not has_duplex_input, "cat-file must not feed a pipe while draining stdout"
    assert batch.kwargs["stdin"].closed, "the input file must be released after the query"


def test_revision_opens_with_large_archived_evidence(tmp_path: Path) -> None:
    root = _large_root(tmp_path)
    command = [
        sys.executable,
        "-m",
        "validator.cli",
        "delivery",
        "revision",
        "open",
        "--feature",
        FEATURE,
        "--model",
        "reviewer/v1",
        "--json",
    ]
    result = subprocess.run(command, cwd=root, capture_output=True, text=True, timeout=2)
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    record = root / ".specs/features" / FEATURE / ".reviews/spec-revision.json"
    assert payload["open"] is True and not payload["error"]
    assert json.loads(record.read_text())["commit"] == payload["commit"]
