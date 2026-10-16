"""Drive one trusted `cargo test` run and publish its report and assertion trace (stdlib only).

1. Build the exact selection with `--no-run` (JSON messages name every test binary).
2. Run the user's exact `cargo test` arguments with this runner installed as Cargo's
   target runner, so Cargo still prepares each binary's environment and fail-fast order.
3. Publish a JUnit report (one suite per binary, ignored and filtered tests kept) and the
   actual assertion trace, plus `runner-gaps` for anything the runner could not observe.
"""

# @spec FR-005: Cargo report and trace publication
#   — .specs/features/085-cargo-execution-runner/spec.md#fr-005

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from validator.execution_cargo_command import CargoTestCommand, parse_cargo_test, runner_variable
from validator.execution_cargo_toolchain import host_triple, runner_paths
from validator.execution_test_budget import read_budget

_LIB_KINDS = frozenset({"lib", "rlib", "dylib", "cdylib", "staticlib", "proc-macro"})
_DOCTESTS = re.compile(r"^\s*Doc-tests\s", re.M)


@dataclass(frozen=True)
class _Context:
    """Runner identity frozen from the capture environment before anything runs."""

    report: Path
    trace: Path
    gaps: Path
    invocation: str
    root: Path
    feature: str
    budget: dict[str, object] | None

    @classmethod
    def from_env(cls) -> _Context:
        """Read the capture's runner-owned variables once, before Cargo or tests run."""
        report = Path(os.environ["LIVESPEC_EXECUTION_REPORT"])
        return cls(
            report,
            Path(os.environ["LIVESPEC_ASSERTION_TRACE"]),
            report.parent / "runner-gaps",
            os.environ["LIVESPEC_EXECUTION_NONCE"],
            Path(os.environ["LIVESPEC_EXECUTION_PROJECT"]),
            os.environ["LIVESPEC_EXECUTION_FEATURE"],
            read_budget(),
        )


def drive(args: list[str]) -> int:
    """Entry: `drive --cargo C --profdata P --cov V -- cargo test ...`.

    Returns 0 when Cargo succeeds, 1 when libtest reported failed tests (as pytest
    does) and Cargo's own exit code for any other failure such as a build error.
    """
    split = args.index("--")
    options = dict(zip(args[:split:2], args[1:split:2], strict=True))
    argv = [options["--cargo"], *args[split + 2 :]]  # The pinned Cargo replaces argv[0].
    context = _Context.from_env()
    command = parse_cargo_test(argv)
    work = context.report.parent / "cargo-runner"
    work.mkdir(mode=0o700)
    entry, wrapper = runner_paths()
    env = {**os.environ, "RUSTC_WORKSPACE_WRAPPER": str(wrapper)}
    env["LLVM_PROFILE_FILE"] = str(work / "stray-%p.profraw")
    build = _relayed(command.build_argv(), env, stdout=False)
    if build.returncode != 0:
        _publish_gaps(context, ["Cargo could not build the selected test binaries"])
        return build.returncode
    binaries = _test_binaries(build.stdout)
    variables = _runner_environment(command, context, work, options, binaries, entry)
    run = _relayed(argv, {**env, **variables}, stdout=True)
    results: list[dict[str, Any]] = [
        json.loads(path.read_text()) for path in sorted(work.glob("results-*.json"))
    ]
    _publish_gaps(context, _gaps(run, binaries, results))
    _publish(context.report, _junit(results))
    _publish(context.trace, _trace(context, results))
    if run.returncode == 0:
        return 0
    failed = any(test["status"] == "failed" for item in results for test in item.get("tests", []))
    return 1 if failed else run.returncode


def _relayed(
    argv: list[str], env: dict[str, str], *, stdout: bool
) -> subprocess.CompletedProcess[str]:
    """Run Cargo and forward its human output (JSON build messages stay internal)."""
    completed = subprocess.run(argv, env=env, capture_output=True, text=True, check=False)
    if stdout:
        sys.stdout.write(completed.stdout)
    sys.stderr.write(completed.stderr)
    return completed


def _runner_environment(
    command: CargoTestCommand,
    context: _Context,
    work: Path,
    options: dict[str, str],
    binaries: dict[str, str],
    entry: Path,
) -> dict[str, str]:
    triples = {host_triple(context.root, dict(os.environ), command.toolchain), *command.targets}
    variables = {runner_variable(triple) for triple in triples}
    config = {
        "work": str(work),
        "root": str(context.root),
        "profdata": options["--profdata"],
        "cov": options["--cov"],
        "binaries": binaries,
        "budget": context.budget,
        "strip_env": sorted({"RUSTC_WORKSPACE_WRAPPER", *variables}),
    }
    path = work / "config.json"
    payload = json.dumps(config).encode()
    _publish(path, payload)
    runner = [sys.executable, "-I", str(entry), "hook", str(path)]
    if any(" " in part for part in runner):
        raise ValueError("Cargo runner paths cannot contain spaces")
    value = " ".join([*runner, hashlib.sha256(payload).hexdigest()])
    return dict.fromkeys(variables, value)


def _test_binaries(messages: str) -> dict[str, str]:
    """Map each built libtest executable to `package/kind/target`."""
    binaries: dict[str, str] = {}
    for line in messages.splitlines():
        message = json.loads(line) if line.startswith("{") else {}
        if message.get("reason") != "compiler-artifact" or not message.get("executable"):
            continue
        if not message.get("profile", {}).get("test"):
            continue
        target = message["target"]
        kinds = set(target["kind"])
        kind = "lib" if kinds & _LIB_KINDS else sorted(kinds)[0]
        package = _package_name(message["package_id"])
        binaries[str(Path(message["executable"]).resolve())] = f"{package}/{kind}/{target['name']}"
    return binaries


def _package_name(package_id: str) -> str:
    """Name from `name version (source)` or `source#name@version` package ids."""
    if " " in package_id:
        return package_id.split(" ", 1)[0]
    source, _, fragment = package_id.partition("#")
    if "@" in fragment:
        return fragment.split("@", 1)[0]
    return source.rstrip("/").rsplit("/", 1)[-1]


def _gaps(
    run: subprocess.CompletedProcess[str], binaries: dict[str, str], results: list[dict[str, Any]]
) -> list[str]:
    gaps = [str(gap) for item in results for gap in item.get("gaps", [])]
    if _DOCTESTS.search(run.stderr):
        gaps.append("Doctests ran outside libtest binaries and cannot be traced")
    handled = {str(item.get("binary")) for item in results}
    if run.returncode == 0:
        gaps.extend(
            f"Test binary ran outside the trusted runner: {identity}"
            for path, identity in sorted(binaries.items())
            if path not in handled
        )
    return gaps


def _junit(results: list[dict[str, Any]]) -> bytes:
    suites = ET.Element("testsuites", name="cargo test")
    for item in sorted(results, key=lambda result: str(result.get("id", ""))):
        if "id" not in item:
            continue
        identity = str(item["id"])
        suite = ET.SubElement(suites, "testsuite", name=identity)
        properties = ET.SubElement(suite, "properties")
        ET.SubElement(properties, "property", name="executable", value=str(item["binary"]))
        for name in item.get("filtered", []):
            ET.SubElement(properties, "property", name="filtered", value=str(name))
        for test in item.get("tests", []):
            case = ET.SubElement(suite, "testcase", classname=identity, name=str(test["name"]))
            if test["status"] == "failed":
                ET.SubElement(case, "failure", message=str(test["message"]))
            elif test["status"] == "skipped":
                ET.SubElement(case, "skipped", message="ignored")
    return ET.tostring(suites, encoding="utf-8")


def _trace(context: _Context, results: list[dict[str, Any]]) -> bytes:
    return json.dumps(
        {
            "schema_version": "1",
            "invocation": context.invocation,
            "project_root": str(context.root),
            "feature": context.feature,
            "assertions": [entry for item in results for entry in item.get("assertions", [])],
        }
    ).encode()


def _publish_gaps(context: _Context, gaps: list[str]) -> None:
    if gaps:
        _publish(context.gaps, json.dumps(gaps).encode())


def _publish(path: Path, payload: bytes) -> None:
    """Create a new file once; a precreated file is a forgery attempt and fails."""
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
