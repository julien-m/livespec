"""Bounded regression for large bidirectional Git batches (feature 094)."""

from __future__ import annotations

import hashlib
import json
import os
import signal
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.integration
def test_revision_git_batch_completes_with_large_duplex_payload(tmp_path: Path) -> None:
    """FR-002: read raw commit blobs without a stdin/stdout pipe deadlock."""
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    bodies = [b"x" * (512 * 1024), b"small\n"]
    objects = [
        subprocess.run(
            ["git", "-C", str(tmp_path), "hash-object", "-w", "--stdin"],
            input=body,
            capture_output=True,
            check=True,
            timeout=3,
        ).stdout.strip()
        for body in bodies
    ]
    # The observed failure fed 605 SHA lines (24,805 bytes) while Git emitted blobs.
    count = 605
    expected = b"".join(
        oid + b" blob " + str(len(body)).encode() + b"\n" + body + b"\n"
        for oid, body in [(objects[0], bodies[0]), *[(objects[1], bodies[1])] * (count - 1)]
    )
    script = """
import hashlib, json, sys
from pathlib import Path
from validator.delivery.revision_commit import _git
payload = (sys.argv[2] + '\\n' + (sys.argv[3] + '\\n') * 604).encode()
result = _git(Path(sys.argv[1]), 'cat-file', '--batch', stdin=payload)
print(json.dumps({'returncode': result.returncode,
                  'digest': hashlib.sha256(result.stdout).hexdigest()}))
"""
    # A separate watchdog can stop a stuck blocking write even when _git's own timeout cannot.
    proc = subprocess.Popen(
        [sys.executable, "-c", script, str(tmp_path), *(oid.decode() for oid in objects)],
        cwd=Path(__file__).resolve().parents[1],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    timed_out = False
    try:
        stdout, stderr = proc.communicate(timeout=3)
    except subprocess.TimeoutExpired:
        timed_out = True
        os.killpg(proc.pid, signal.SIGKILL)
        stdout, stderr = proc.communicate()
    assert not timed_out, "Git batch stalled with both stdin and stdout pipes populated"
    assert proc.returncode == 0, stderr.decode()
    assert json.loads(stdout) == {
        "returncode": 0,
        "digest": hashlib.sha256(expected).hexdigest(),
    }
