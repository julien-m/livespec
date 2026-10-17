"""Distinct genuine Vitest preparation and runtime deadline/cleanup evidence."""

from __future__ import annotations

import json
import os
import time
from collections.abc import Callable
from pathlib import Path

import pytest
from click.testing import Result

from tests.execution_vitest_fixture import FEATURE, VitestProject
from tests.execution_vitest_fixture import vitest_dependencies as vitest_dependencies
from tests.execution_vitest_fixture import vitest_project as vitest_project
from validator import execution_vitest_provenance
from validator.execution_evidence import EvidenceVerification, verify_execution_observation

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


@pytest.mark.parametrize(
    "phase,value,milliseconds",
    [
        ("test", "0", 120),
        ("hook", "0", 120),
        ("test", "-1", 120),
        ("hook", "NaN", 120),
        ("test", "Infinity", 120),
        ("test", "30", 30),
        ("hook", "300", 120),
        ("test", "'invalid'", None),
    ],
)
def test_consumer_timeouts_cannot_disable_owned_limits(
    vitest_project: VitestProject,
    monkeypatch: pytest.MonkeyPatch,
    phase: str,
    value: str,
    milliseconds: int | None,
) -> None:
    """Observe native test/hook expiry with nonpositive, nonfinite and tighter options."""
    from validator import test_budgets

    monkeypatch.setitem(test_budgets.DEFAULT_TEST_SECONDS, "unit", 0.12)
    field = "testTimeout" if phase == "test" else "hookTimeout"
    (vitest_project.root / "vitest.config.ts").write_text(
        "export default {test:{maxWorkers:1,minWorkers:1," + field + ":" + value + "}};"
    )
    delay = "await new Promise(resolve => setTimeout(resolve,400));"
    body = "test('bounded', async () => { " + delay + "expect(1).toBe(1); });"
    if phase == "hook":
        body = "import {beforeEach} from 'vitest'; beforeEach(async () => { " + delay + "}); "
        body += "test('bounded', () => {expect(1).toBe(1);});"
    vitest_project.write(body)
    receipt = vitest_project.capture(timeout=3)
    capture = json.loads((receipt.parent / "capture.json").read_text())
    assert capture["exit_code"] == 1, (receipt.parent / "stdout").read_text()
    diagnostic = (receipt.parent / "stderr").read_text() + (receipt.parent / "stdout").read_text()
    if (receipt.parent / "report").is_file():
        diagnostic += (receipt.parent / "report").read_text()
    if milliseconds is None:
        assert "Invalid configured timeout" in diagnostic, diagnostic
    else:
        label = "Test" if phase == "test" else "Hook"
        assert f"{label} timed out in {milliseconds}ms" in diagnostic, diagnostic
    assert not verify_execution_observation(receipt, vitest_project.root, FEATURE, "passed").valid


@pytest.mark.parametrize(
    "mode",
    ["within-deadline", "expired-verification", "completion-write-error", "completion-late"],
)
def test_cli_final_verification_keeps_original_deadline_and_invalidates_timeout(
    vitest_project: VitestProject,
    monkeypatch: pytest.MonkeyPatch,
    mode: str,
) -> None:
    """Use actual capture/watchdog and later public reads, including failed completion writes."""
    import errno

    from typer.testing import CliRunner

    from validator import execution_capture_storage, execution_evidence, test_budgets
    from validator.cli import app
    from validator.execution_deadline import current_deadline

    vitest_project.write("test('actual matcher', () => {expect(1).toBe(1);});")
    captured: list[tuple[Path, bytes]] = []
    real_provenance = execution_evidence._current_provenance
    real_write = execution_capture_storage._write_new
    expire = mode in {"expired-verification", "completion-late"}
    write_error = mode == "completion-write-error"

    def hash_with_cost(recorded: dict[str, str]) -> dict[str, str]:
        captured.extend(
            (p, p.read_bytes())
            for p in vitest_project.root.glob(".specs/.execution/*/receipt.json")
        )
        scope = current_deadline()
        if scope is not None:
            assert scope.argv == vitest_project.command()
            assert scope.end <= started + 4.05
        time.sleep(4.3 if mode == "expired-verification" else 0.01)
        return real_provenance(recorded)

    def write_completion(descriptor: int, name: str, data: bytes) -> None:
        if write_error and name == "verification-complete.json":
            real_write(descriptor, name, data)
            assert not verify_execution_observation(
                captured[0][0], vitest_project.root, FEATURE, "passed"
            ).valid, "Incomplete publication qualified during the storage failure window"
            raise OSError(errno.ENOSPC, "controlled completion storage exhaustion")
        real_write(descriptor, name, data)

    with monkeypatch.context() as scoped:
        scoped.chdir(vitest_project.root)
        scoped.setattr(test_budgets, "DEFAULT_COMMAND_SECONDS", 4.0)
        scoped.setattr(execution_capture_storage, "_write_new", write_completion)
        if mode == "completion-late":
            scoped.setattr(os, "link", _late_completion_link(os.link))
        scoped.setattr(execution_evidence, "_current_provenance", hash_with_cost)
        started = time.monotonic()
        result = CliRunner().invoke(app, _observation_arguments(vitest_project))
        elapsed = time.monotonic() - started
    fresh = _assert_final_capture(captured, vitest_project, result, elapsed, expire, write_error)
    assert fresh.valid is not (expire or write_error), fresh.gaps


def _late_completion_link(real_link: Callable[..., None]) -> Callable[..., None]:
    """Publish the actual link, then hold its syscall wrapper across the owned deadline."""

    def delayed(
        src: str, dst: str, *, src_dir_fd: int, dst_dir_fd: int, follow_symlinks: bool
    ) -> None:
        real_link(
            src, dst, src_dir_fd=src_dir_fd, dst_dir_fd=dst_dir_fd, follow_symlinks=follow_symlinks
        )
        time.sleep(4.3)

    return delayed


def _assert_final_capture(
    captured: list[tuple[Path, bytes]],
    vitest_project: VitestProject,
    result: Result,
    elapsed: float,
    expire: bool,
    write_error: bool,
) -> EvidenceVerification:
    """Re-read actual public evidence after success or failed final publication."""
    receipt, original_reference = captured[0]
    fresh = verify_execution_observation(receipt, vitest_project.root, FEATURE, "passed")
    assert receipt.read_bytes() == original_reference, "Historical capture reference was rewritten"
    assert result.exit_code == (124 if expire else 1 if write_error else 0), result.output
    assert elapsed < 4.2, (elapsed, result.output)
    if expire or write_error:
        assert all(
            not (receipt.parent / name).exists()
            for name in ("verification-complete.json", "verification-accepted.json")
        )
        marker = receipt.parent / "verification-accepted.json"
        if not marker.exists():
            marker.write_text("{")
        assert not verify_execution_observation(
            receipt, vitest_project.root, FEATURE, "passed"
        ).valid
    return fresh


def _observation_arguments(project: VitestProject) -> list[str]:
    """Use the exact real Node command through the public observation CLI."""
    import shlex

    return [
        "test",
        "--feature",
        FEATURE,
        "--execution-command",
        shlex.join(project.command()),
        "--execution-observation",
        "passed",
        "--report-adapter",
        "junit",
    ]
