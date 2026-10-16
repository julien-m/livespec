"""Cargo target runner hook: run each selected test in its own traced process (stdlib only).

Cargo invokes this hook once per test binary, with the environment Cargo prepares
for tests (working directory, `CARGO_*` variables, dynamic library paths) plus the
caller's variables. The hook lists the selection with libtest itself, runs every
listed test with `--exact` in a separate process with its own coverage profile and
libtest log, then records statuses and executed assertions for the driver.
"""

# @spec FR-002: Per-test libtest execution
#   — .specs/features/085-cargo-execution-runner/spec.md#fr-002

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import nullcontext
from dataclasses import dataclass, field
from pathlib import Path

from validator.execution_cargo_command import LibtestSelection, parse_libtest
from validator.execution_cargo_coverage import (
    CoverageError,
    CoverageTools,
    SourceIndex,
    executed_assertions,
    panic_locations,
)
from validator.execution_rust_source import RustAssertion
from validator.execution_test_budget import resolve_test_budget, test_watchdog

_STATUS = {"ok": "passed", "failed": "failed", "ignored": "skipped"}


@dataclass
class _Test:
    name: str
    status: str = "failed"
    message: str = ""
    output: str = ""
    assertions: list[dict[str, str | int]] = field(default_factory=list[dict[str, str | int]])
    gaps: list[str] = field(default_factory=list[str])


@dataclass(frozen=True)
class _Hook:
    binary: str
    binary_id: str
    work: Path
    tools: CoverageTools
    index: SourceIndex
    selection: LibtestSelection
    env: dict[str, str]
    budget: dict[str, object] | None = None


def hook(args: list[str]) -> int:
    """Entry: `hook <config> <config-sha256> <binary> [libtest args...]`."""
    config_path, config_sha, binary, *libtest_args = args
    data = Path(config_path).read_bytes()
    if hashlib.sha256(data).hexdigest() != config_sha:
        print("livespec cargo runner: configuration changed", file=sys.stderr)
        return 2
    config = json.loads(data)
    resolved = str(Path(binary).resolve())
    binary_id = config["binaries"].get(resolved)
    work = Path(config["work"])
    if binary_id is None:
        _write(work, {"binary": resolved, "gaps": [f"Unlisted test binary ran: {resolved}"]})
        return subprocess.run([binary, *libtest_args], check=False).returncode
    env = {key: value for key, value in os.environ.items() if key not in config["strip_env"]}
    context = _Hook(
        resolved,
        binary_id,
        work,
        CoverageTools(config["profdata"], config["cov"]),
        SourceIndex(Path(config["root"])),
        parse_libtest(libtest_args),
        env,
        config.get("budget"),
    )
    return _run_binary(context, libtest_args)


def _run_binary(context: _Hook, libtest_args: list[str]) -> int:
    listed = _list(context, context.selection.list_args())
    every = _list(context, ["--include-ignored"] if context.selection.ignored else [])
    if listed is None or every is None:
        gap = f"Test binary without a libtest harness cannot be traced: {context.binary_id}"
        _write(context.work, {"binary": context.binary, "id": context.binary_id, "gaps": [gap]})
        return subprocess.run([context.binary, *libtest_args], check=False).returncode
    threads = context.selection.threads or _default_threads(context.env)
    with ThreadPoolExecutor(max_workers=threads) as pool:
        numbers = range(len(listed))
        tests = list(pool.map(_run_test, [context] * len(listed), numbers, listed))
    _relay(tests, len(set(every) - set(listed)))
    _write(
        context.work,
        {
            "binary": context.binary,
            "id": context.binary_id,
            "tests": [{"name": t.name, "status": t.status, "message": t.message} for t in tests],
            "filtered": sorted(set(every) - set(listed)),
            "assertions": [item for test in tests for item in test.assertions],
            "gaps": [gap for test in tests for gap in test.gaps],
        },
    )
    return 101 if any(test.status == "failed" for test in tests) else 0


def _default_threads(env: dict[str, str]) -> int:
    value = env.get("RUST_TEST_THREADS", "")
    return int(value) if value.isdigit() and int(value) > 0 else os.cpu_count() or 1


def _list(context: _Hook, args: list[str]) -> list[str] | None:
    profile = context.work / f"list-{uuid.uuid4().hex}-%p.profraw"
    completed = subprocess.run(
        [context.binary, "--list", "--format", "terse", *args],
        env={**context.env, "LLVM_PROFILE_FILE": str(profile)},
        capture_output=True,
        text=True,
        check=False,
    )
    _remove_profiles(profile)
    names = [
        line[: -len(": test")] for line in completed.stdout.splitlines() if line.endswith(": test")
    ]
    if completed.returncode != 0 or len(names) != len(completed.stdout.splitlines()):
        return None
    return names


def _run_test(context: _Hook, number: int, name: str) -> _Test:
    """Bound exact libtest startup, body and evidence cleanup together."""
    category = "integration" if context.binary_id.split("/")[1:2] == ["test"] else "unit"
    budget = (
        resolve_test_budget(context.budget, f"{context.binary_id}::{name}", category)
        if context.budget
        else None
    )
    with test_watchdog(budget) if budget else nullcontext():
        return _run_test_inner(context, number, name)


def _run_test_inner(context: _Hook, number: int, name: str) -> _Test:
    stem = context.work / f"{hashlib.sha256(context.binary.encode()).hexdigest()[:12]}-{number}"
    log = stem.with_suffix(".log")
    profile = Path(f"{stem}-%p.profraw")
    argv = [context.binary, "--exact", name, "--test-threads=1", "--nocapture"]
    argv += [
        "--logfile",
        str(log),
        *([context.selection.ignored] if context.selection.ignored else []),
    ]
    completed = subprocess.run(
        argv,
        env={**context.env, "LLVM_PROFILE_FILE": str(profile)},
        capture_output=True,
        check=False,
    )
    stdout = completed.stdout.decode(errors="replace")
    stderr = completed.stderr.decode(errors="replace")
    test = _Test(name, output=stdout + stderr)
    test.status = _status(log, name, completed.returncode, test)
    profiles = sorted(stem.parent.glob(f"{stem.name}-*.profraw"))
    _assertions(context, test, stdout, stderr, profiles, stem)
    _remove_profiles(profile)
    log.unlink(missing_ok=True)
    return test


def _status(log: Path, name: str, code: int, test: _Test) -> str:
    """Trust only a single libtest log entry for this exact test, consistent with the exit."""
    lines = log.read_text(errors="replace").splitlines() if log.is_file() else []
    # Entries read `<kind>[: <ignore reason>] <test name>`.
    statuses = [
        _STATUS.get(line.removesuffix(f" {name}").split(":", 1)[0], "")
        for line in lines
        if line.endswith(f" {name}")
    ]
    expected_code = 101 if statuses == ["failed"] else 0
    if len(statuses) != 1 or len(lines) != 1 or not statuses[0] or code != expected_code:
        test.message = f"libtest reported no single consistent result (exit {code})"
        test.gaps.append(f"Unobservable test result: {test.name}")
        return "failed"
    if statuses[0] == "failed":
        test.message = "test failed"
    return statuses[0]


def _assertions(
    context: _Hook, test: _Test, stdout: str, stderr: str, profiles: list[Path], stem: Path
) -> None:
    test_id = f"{context.binary_id}::{test.name}"
    cwd = Path.cwd()
    panics = [context.index.at_panic(location, cwd) for location in panic_locations(stderr)]
    for found in panics:
        if found is not None:
            test.assertions.append(_record(test_id, *found, "failed"))
    should_panic = f"test {test.name} - should panic ..." in stdout
    if test.status != "passed" or panic_locations(stderr) or should_panic:
        return  # Region counts cannot tell which statements ran after a panic.
    try:
        executed = executed_assertions(context.tools, context.binary, profiles, stem, context.index)
    except CoverageError as exc:
        test.gaps.append(f"Coverage unavailable for {test_id}: {exc}")
        return
    test.assertions.extend(_record(test_id, path, item, "passed") for path, item in executed)


def _record(test_id: str, path: Path, item: RustAssertion, status: str) -> dict[str, str | int]:
    return {
        "test_id": test_id,
        "path": str(path),
        "line": item.line,
        "assertion": item.text,
        "status": status,
    }


def _relay(tests: list[_Test], filtered: int) -> None:
    """Print a libtest-like transcript; failed tests show their captured output."""
    print(f"\nrunning {len(tests)} tests")
    for test in tests:
        word = {"passed": "ok", "failed": "FAILED", "skipped": "ignored"}[test.status]
        print(f"test {test.name} ... {word}")
    failed = [test for test in tests if test.status == "failed"]
    for test in failed:
        print(f"\n---- {test.name} stdout ----\n{test.output}")
    counts = {status: sum(t.status == status for t in tests) for status in _STATUS.values()}
    outcome = "FAILED" if failed else "ok"
    print(
        f"\ntest result: {outcome}. {counts['passed']} passed; {counts['failed']} failed; "
        f"{counts['skipped']} ignored; 0 measured; {filtered} filtered out\n",
        flush=True,
    )


def _remove_profiles(pattern: Path) -> None:
    prefix = pattern.name.split("%p", 1)[0]
    for path in pattern.parent.glob(f"{prefix}*.profraw"):
        path.unlink(missing_ok=True)


def _write(work: Path, payload: dict[str, object]) -> None:
    descriptor = os.open(
        work / f"results-{uuid.uuid4().hex}.json",
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600,
    )
    with os.fdopen(descriptor, "w") as stream:
        json.dump(payload, stream)
