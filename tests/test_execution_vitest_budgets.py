"""Distinct genuine Vitest preparation and runtime deadline/cleanup evidence."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pytest

from tests.execution_vitest_fixture import FEATURE, VitestProject
from tests.execution_vitest_fixture import vitest_dependencies as vitest_dependencies
from tests.execution_vitest_fixture import vitest_project as vitest_project
from validator import execution_vitest_provenance
from validator.execution_evidence import verify_execution_observation

pytestmark = pytest.mark.integration


def _assert_timeout(project: VitestProject, receipt: Path) -> None:
    """Require an actual managed timeout that proves neither observation purpose."""
    capture = json.loads((receipt.parent / "capture.json").read_text())
    assert capture["exit_code"] == 124
    assert capture["budget"]["timed_out"]
    for purpose in ("passed", "red"):
        result = verify_execution_observation(receipt, project.root, FEATURE, purpose)
        assert not result.valid
        assert result.gaps


def test_preparation_hash_expiry_never_reaches_test_body(
    vitest_project: VitestProject, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Interrupt genuine preparation hashing under the real managed wall clock."""
    markers = vitest_project.root / ".specs/.execution"
    markers.mkdir(parents=True)
    entered = markers / "preparation-entered"
    body = markers / "body-entered"
    vitest_project.write(
        "import {writeFileSync} from 'node:fs';\n"
        f"test('must not execute', () => {{writeFileSync({json.dumps(str(body))}, 'body');"
        "expect(1).toBe(1);});"
    )
    original = execution_vitest_provenance._tree_identity

    def bounded_hash_delay(root: Path) -> str:
        """Finish the genuine installed-module hash before controlled real-time blocking."""
        identity = original(root)
        if root.name == "node_modules":
            entered.write_text(identity)
            # Deliberately exceed the two-second command cap; its actual SIGALRM interrupts sleep.
            time.sleep(3)
        return identity

    with monkeypatch.context() as preparation:
        preparation.setattr(execution_vitest_provenance, "_tree_identity", bounded_hash_delay)
        receipt = vitest_project.capture(timeout=2)
    # @spec AC-004: Preparation expiry is distinct from runtime and is nonqualifying.
    # — .specs/features/096-node-vitest-execution/spec.md#ac-004
    assert len(entered.read_text()) == 64
    assert not body.exists()
    _assert_timeout(vitest_project, receipt)


def _child_gone(pid: int) -> bool:
    """Check the actual owned child PID without treating permissions as absence."""
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return True
    return False


def test_runtime_expiry_terminates_owned_descendant_and_heartbeat(
    vitest_project: VitestProject,
) -> None:
    """Reach a real Vitest body and descendant, then prove process-group cleanup."""
    markers = vitest_project.root / ".specs/.execution"
    markers.mkdir(parents=True)
    body = markers / "runtime-entered"
    heartbeat = markers / "child-heartbeat"
    pid_file = markers / "child-pid"
    child = (
        "const fs=require('node:fs');"
        "fs.writeFileSync(process.argv[2],String(process.pid));"
        "fs.appendFileSync(process.argv[1],'tick\\n');"
        "setInterval(()=>fs.appendFileSync(process.argv[1],'tick\\n'),20);"
    )
    # The child inherits the runner's group; blocking requires outer process cleanup.
    vitest_project.write(
        "import {writeFileSync} from 'node:fs';\n"
        "import {spawn} from 'node:child_process';\n"
        f"test('hang after child starts', () => {{writeFileSync({json.dumps(str(body))},'body');"
        f"spawn(process.execPath,['-e',{json.dumps(child)},{json.dumps(str(heartbeat))},"
        f"{json.dumps(str(pid_file))}],{{stdio:'ignore'}});"
        "expect(1).toBe(1); while(true) {} });"
    )
    receipt = vitest_project.capture(timeout=5)
    assert body.read_text() == "body"
    pid = int(pid_file.read_text())
    before = heartbeat.read_bytes()
    assert before.startswith(b"tick\n")
    # @spec AC-004: Runtime expiry kills the reached owned child within cleanup bounds.
    # — .specs/features/096-node-vitest-execution/spec.md#ac-004
    cleanup_end = time.monotonic() + 0.5
    while not _child_gone(pid) and time.monotonic() < cleanup_end:
        time.sleep(0.02)
    assert _child_gone(pid), f"Owned child {pid} survived managed cleanup"
    time.sleep(0.08)
    assert heartbeat.read_bytes() == before
    _assert_timeout(vitest_project, receipt)
