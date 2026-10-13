"""Turn one test's LLVM coverage profile into executed assertion invocations (stdlib only).

The workspace wrapper compiles libtest harness crates with `-C instrument-coverage`.
Each test runs in its own process with its own profile, so a region count greater
than zero at an assertion's first character proves that this test reached and
evaluated that assertion. The runner only infers passing assertions from tests that
passed without any observed panic; failing assertions come from panic locations.
"""

# @spec FR-003: Executed assertions from per-test coverage
#   — .specs/features/085-cargo-execution-runner/spec.md#fr-003

from __future__ import annotations

import bisect
import json
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from validator.execution_rust_source import RustAssertion, rust_assertions

_PANIC = re.compile(
    r"panicked at (?:'.*', )?(?P<file>[^\n]+?):(?P<line>\d+):(?P<col>\d+):?\s*$", re.M
)


class CoverageError(Exception):
    """A profile could not be merged or exported; the trace would be incomplete."""


@dataclass(frozen=True)
class CoverageTools:
    """Pinned llvm-profdata and llvm-cov executables."""

    profdata: str
    cov: str


class SourceIndex:
    """Cache assertion invocations of project Rust files read during one hook."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self._files: dict[Path, list[RustAssertion]] = {}

    def assertions(self, path: Path) -> list[RustAssertion]:
        """Assertions of a project file (empty outside the project or non-Rust)."""
        path = path.resolve()
        if path.suffix != ".rs" or not path.is_relative_to(self.root) or not path.is_file():
            return []
        if path not in self._files:
            self._files[path] = rust_assertions(path.read_text(encoding="utf-8"))
        return self._files[path]

    def at_panic(
        self, location: tuple[str, int, int], cwd: Path
    ) -> tuple[Path, RustAssertion] | None:
        """Resolve a `file:line:col` panic location to the assertion invoked there."""
        relative, line, column = location
        for base in (cwd, *cwd.parents):
            candidate = Path(os.path.normpath(base / relative))
            for item in self.assertions(candidate):
                if item.line == line and column in (item.column, item.byte_column):
                    return candidate.resolve(), item
            if base == self.root:
                break
        return None


def panic_locations(stderr: str) -> list[tuple[str, int, int]]:
    """Every panic location printed by the default panic hook."""
    return [
        (match["file"], int(match["line"]), int(match["col"])) for match in _PANIC.finditer(stderr)
    ]


def executed_assertions(
    tools: CoverageTools, binary: str, profiles: list[Path], output: Path, index: SourceIndex
) -> list[tuple[Path, RustAssertion]]:
    """Assertions whose first character lies in a region this profile executed.

    Raises:
        CoverageError: No profile was written or LLVM tools rejected it.
    """
    if not profiles:
        raise CoverageError("the instrumented test wrote no coverage profile")
    merged = output.with_suffix(".profdata")
    _tool([tools.profdata, "merge", "-sparse", *map(str, profiles), "-o", str(merged)])
    exported = _tool(
        [
            tools.cov,
            "export",
            "--format=text",
            "--skip-functions",
            f"--instr-profile={merged}",
            binary,
        ]
    )
    merged.unlink(missing_ok=True)
    try:
        files = json.loads(exported)["data"][0]["files"]
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        raise CoverageError(f"unexpected llvm-cov export: {exc}") from exc
    found: list[tuple[Path, RustAssertion]] = []
    for item in files:
        path = Path(item["filename"]).resolve()
        segments = [tuple(segment) for segment in item["segments"]]
        found.extend(
            (path, assertion)
            for assertion in index.assertions(path)
            if _executed(segments, assertion.line, assertion.byte_column)
        )
    return found


def _executed(segments: list[tuple[object, ...]], line: int, column: int) -> bool:
    """The region in effect at (line, column) has a positive execution count."""
    keys = [(int(str(segment[0])), int(str(segment[1]))) for segment in segments]
    position = bisect.bisect_right(keys, (line, column)) - 1
    if position < 0:
        return False
    _, _, count, has_count, _, *rest = segments[position]
    is_gap = bool(rest[0]) if rest else False
    return bool(has_count) and not is_gap and int(str(count)) > 0


def _tool(argv: list[str]) -> str:
    try:
        completed = subprocess.run(argv, capture_output=True, text=True, timeout=300, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise CoverageError(f"{Path(argv[0]).name} failed: {exc}") from exc
    if completed.returncode != 0:
        detail = completed.stderr.strip().splitlines()[-1:] or ["no detail"]
        raise CoverageError(f"{Path(argv[0]).name} rejected the profile: {detail[0]}")
    return completed.stdout
