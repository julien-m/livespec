"""Parse mutmut output into structured mutation-test results."""

# @spec FR-005: Mutmut result parsing — .specs/features/017-driver-python/spec.md#fr-005

from __future__ import annotations

import json
import re
import subprocess
from typing import TypedDict

_SURVIVOR_PATTERN = re.compile(r"([a-zA-Z0-9_./-]+\.py):(\d+)")


class SurvivingMutant(TypedDict):
    """Structured description of one surviving mutant."""

    file: str
    line: int
    description: str


class MutmutParseResult(TypedDict):
    """Normalized mutmut summary used by driver code and tests."""

    killed: int
    survived: int
    timeout: int
    score: float
    survivors: list[SurvivingMutant]


def _empty_result() -> MutmutParseResult:
    """Return the default parse result used for missing or invalid output."""
    return {
        "killed": 0,
        "survived": 0,
        "timeout": 0,
        "score": 0.0,
        "survivors": [],
    }


def _run_mutmut_results(argv: list[str], *, timeout: float) -> str | None:
    """Execute mutmut and return stdout when the command succeeds.

    Args:
        argv: Exact mutmut argv to execute.
        timeout: Maximum execution time in seconds.

    Returns:
        Captured stdout when mutmut exits successfully, otherwise ``None``.
    """
    try:
        # The driver expects mutmut to emit result text on stdout and to use a
        # non-zero exit code when the command itself cannot complete.
        completed = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (FileNotFoundError, subprocess.SubprocessError, OSError):
        return None

    if completed.returncode != 0 or not completed.stdout:
        return None
    return completed.stdout


def parse_mutmut_results(json_output: str | None) -> MutmutParseResult:
    """Parse mutmut results from provided JSON or from a local mutmut command.

    Args:
        json_output: Optional JSON payload produced by ``mutmut results``.

    Returns:
        Structured killed/survived counts, mutation score, and survivor details.
    """
    if json_output:
        try:
            data = json.loads(json_output)
        except json.JSONDecodeError:
            return _empty_result()

        killed = int(data.get("killed", 0))
        survived = int(data.get("survived", 0))
        timeout = int(data.get("timeout", 0))
    else:
        command_output = _run_mutmut_results(
            ["mutmut", "results", "--use-coverage"],
            timeout=30,
        )
        if command_output is None:
            return _empty_result()
        return parse_mutmut_results(command_output)

    return {
        "killed": killed,
        "survived": survived,
        "timeout": timeout,
        "score": compute_mutation_score(killed, survived),
        "survivors": extract_surviving_mutants(),
    }


def compute_mutation_score(killed: int, survived: int) -> float:
    """Compute the percentage of mutants killed by the test suite.

    Args:
        killed: Number of mutants killed by tests.
        survived: Number of mutants that escaped.

    Returns:
        Mutation score as a percentage in the range ``0.0`` to ``100.0``.
    """
    total = killed + survived
    if total == 0:
        return 0.0
    return (killed / total) * 100.0


def extract_surviving_mutants() -> list[SurvivingMutant]:
    """Extract surviving mutant locations from ``mutmut results`` text output.

    Returns:
        Surviving mutant descriptors with file, line, and raw description text.
    """
    survivors: list[SurvivingMutant] = []
    command_output = _run_mutmut_results(["mutmut", "results"], timeout=10)
    if command_output is None:
        return survivors

    for line in command_output.splitlines():
        if "survived" not in line.lower() and "to-kill" not in line.lower():
            continue
        # This regex matches Python source paths followed by a source line number.
        match = _SURVIVOR_PATTERN.search(line)
        if match is None:
            continue
        survivors.append(
            {
                "file": match.group(1),
                "line": int(match.group(2)),
                "description": line.strip(),
            }
        )

    return survivors
