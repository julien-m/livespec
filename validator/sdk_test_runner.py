"""SDK test runner — subprocess wrapper for Level 3b pytest invocation.

Delegates to pytest via subprocess.Popen, streaming output in real time.
Does NOT import claude-agent-sdk; the CLI probes availability via
importlib.util.find_spec before instantiating this service.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from .exceptions import SdkTestRunError

# @spec FR-008: SdkTestResult schema — .specs/features/002-layer-3-cli-surface/spec.md#fr-008
_PASSED_RE = re.compile(r"(\d+) passed")
_FAILED_RE = re.compile(r"(\d+) failed")
_SKIPPED_RE = re.compile(r"(\d+) skipped")


@dataclass
class SdkTestResult:
    """Result of a Level 3b test run.

    Attributes:
        passed: Number of tests that passed.
        failed: Number of tests that failed.
        skipped: Number of tests that were skipped.
        total: Sum of passed + failed + skipped.
        exit_code: Raw pytest returncode.
        raw_output: Full captured stdout+stderr from pytest.
    """

    passed: int
    failed: int
    skipped: int
    total: int
    exit_code: int
    raw_output: str


def _parse_pytest_summary(output: str) -> dict[str, int]:
    """Parse pytest terminal summary line for pass/fail/skip counts.

    Falls back to zeros if the summary line is absent or unparseable.

    Args:
        output: Full pytest stdout+stderr output.

    Returns:
        Dict with keys passed, failed, skipped.
    """
    passed = 0
    failed = 0
    skipped = 0

    m = _PASSED_RE.search(output)
    if m:
        passed = int(m.group(1))
    m = _FAILED_RE.search(output)
    if m:
        failed = int(m.group(1))
    m = _SKIPPED_RE.search(output)
    if m:
        skipped = int(m.group(1))

    return {"passed": passed, "failed": failed, "skipped": skipped}


def _build_pytest_cmd(feature_slug: str | None) -> list[str]:
    """Build the pytest command for Level 3b tests.

    Uses sys.executable -m pytest to ensure correct virtualenv.

    Args:
        feature_slug: Optional underscore-normalized slug for -k filter.

    Returns:
        Command list for subprocess.Popen.
    """
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests/integration/",
        "-m",
        "level_3b",
        "-v",
        "--tb=short",
    ]
    # @spec FR-006: Append -k filter — .specs/features/002-layer-3-cli-surface/spec.md#fr-006
    if feature_slug is not None:
        cmd.extend(["-k", feature_slug])
    return cmd


# @spec FR-007: Forward budget env var — .specs/features/002-layer-3-cli-surface/spec.md#fr-007
def _build_subprocess_env(budget_usd: float | None) -> dict[str, str]:
    """Build environment dict for the pytest subprocess.

    Inherits current environment and optionally sets budget.

    Args:
        budget_usd: Budget limit in USD, or None to skip.

    Returns:
        Environment dict for subprocess.Popen.
    """
    env = os.environ.copy()
    if budget_usd is not None:
        env["LIVESPEC_TEST_BUDGET_USD"] = str(budget_usd)
    return env


# @spec FR-004: Subprocess invocation for level_3b tests — .specs/features/002-layer-3-cli-surface/spec.md#fr-004  # noqa: E501
class SdkTestRunner:
    """Service that wraps pytest subprocess for Level 3b SDK-isolated tests.

    Attributes:
        project_root: Path to the project root (parent of .specs/).
    """

    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root

    def run(
        self,
        feature_slug: str | None = None,
        budget_usd: float | None = None,
    ) -> SdkTestResult:
        """Run Level 3b tests via subprocess.

        Streams pytest output to stderr in real time. Parses the summary
        line for pass/fail/skip counts.

        Args:
            feature_slug: Optional slug to narrow via -k filter.
            budget_usd: Optional budget limit forwarded via env var.

        Returns:
            SdkTestResult with counts and exit code.

        Raises:
            SdkTestRunError: If the subprocess cannot be started.
        """
        cmd = _build_pytest_cmd(feature_slug)
        env = _build_subprocess_env(budget_usd)

        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                cwd=str(self.project_root),
                env=env,
            )
        except (FileNotFoundError, PermissionError) as exc:
            raise SdkTestRunError(cmd, str(exc)) from exc

        # @spec FR-009: Stream pytest output to stderr — .specs/features/002-layer-3-cli-surface/spec.md#fr-009  # noqa: E501
        lines: list[str] = []
        assert proc.stdout is not None  # guaranteed by PIPE
        for raw_line in iter(proc.stdout.readline, b""):
            line = raw_line.decode("utf-8", errors="replace")
            sys.stderr.write(line)
            lines.append(line)

        proc.wait()
        raw_output = "".join(lines)
        counts = _parse_pytest_summary(raw_output)

        return SdkTestResult(
            passed=counts["passed"],
            failed=counts["failed"],
            skipped=counts["skipped"],
            total=counts["passed"] + counts["failed"] + counts["skipped"],
            exit_code=proc.returncode,
            raw_output=raw_output,
        )
