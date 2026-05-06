# @spec FR-005: Mutmut result parsing — .specs/features/017-driver-python/spec.md#fr-005
"""
Mutmut result parsing and mutation score computation.
"""

import json
import re
import subprocess


def parse_mutmut_results(json_output: str | None) -> dict:
    """
    Parse mutmut results from JSON output or run mutmut to get results.

    Args:
        json_output: Optional JSON output from `mutmut results --json`

    Returns:
        Dictionary with keys: killed, survived, timeout, score, survivors
    """
    if json_output:
        try:
            data = json.loads(json_output)
            killed = data.get("killed", 0)
            survived = data.get("survived", 0)
            timeout = data.get("timeout", 0)
        except Exception:
            return {"killed": 0, "survived": 0, "timeout": 0, "score": 0, "survivors": []}
    else:
        # Try to run mutmut results --json
        try:
            result = subprocess.run(
                ["mutmut", "results", "--use-coverage"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0 and result.stdout:
                return parse_mutmut_results(result.stdout)
        except Exception:
            pass
        return {"killed": 0, "survived": 0, "timeout": 0, "score": 0, "survivors": []}

    score = compute_mutation_score(killed, survived)
    survivors = extract_surviving_mutants(killed, survived, timeout)

    return {
        "killed": killed,
        "survived": survived,
        "timeout": timeout,
        "score": score,
        "survivors": survivors,
    }


def compute_mutation_score(killed: int, survived: int) -> float:
    """
    Compute mutation score as percentage of mutants killed.

    Args:
        killed: Number of mutants killed (tests failed)
        survived: Number of mutants that survived (tests passed)

    Returns:
        Mutation score as percentage (0-100), or 0 if no mutants
    """
    total = killed + survived
    if total == 0:
        return 0.0
    return (killed / total) * 100


def extract_surviving_mutants(
    killed: int, survived: int, timeout: int
) -> list[dict]:
    """
    Extract surviving mutants from mutmut output.

    Args:
        killed: Number of killed mutants
        survived: Number of surviving mutants
        timeout: Number of timeout mutants

    Returns:
        List of surviving mutant dicts with file:line references
    """
    survivors = []
    try:
        result = subprocess.run(
            ["mutmut", "results"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            # Parse surviving mutant lines from output
            # Format typically: "file.py:123: mutant_type"
            for line in result.stdout.split("\n"):
                if "survived" in line.lower() or "to-kill" in line.lower():
                    match = re.search(r"([a-z0-9_/]+\.py):(\d+)", line)
                    if match:
                        survivors.append(
                            {
                                "file": match.group(1),
                                "line": int(match.group(2)),
                                "description": line.strip(),
                            }
                        )
    except Exception:
        pass

    return survivors
