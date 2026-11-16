"""Confined file selection and argv construction for existing journey tests."""

from __future__ import annotations

import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from .schema import ExistingTestReference


# @spec FR-002: Existing runner configuration
# — .specs/features/123-existing-test-journeys/spec.md#fr-002
def reference_files(project_root: Path, reference: ExistingTestReference) -> list[Path]:
    """Resolve real test/config files within the consumer project, including symlink targets."""
    root = project_root.resolve()
    files: list[Path] = []
    for value in (reference.path, reference.config):
        if value is None:
            continue
        path = (root / value).resolve(strict=True)
        if not path.is_relative_to(root) or not path.is_file():
            raise ValueError(f"existing test file must stay inside the project: {value}")
        files.append(path)
    return files


def reference_command(
    project_root: Path, runner: str, reference: ExistingTestReference
) -> list[str]:
    """Build one bounded runner invocation without a shell or automatic package installation."""
    files = reference_files(project_root, reference)
    relative = files[0].relative_to(project_root.resolve()).as_posix()
    # Playwright interprets file arguments as regular expressions; preserve literal selection.
    if runner == "playwright":
        command = ["npx", "--no-install", "playwright", "test", f"^{re.escape(str(files[0]))}$"]
        config_flag, selector_flag = "--config", "--grep"
    elif runner == "vitest":
        # Vitest CLI file filters are substrings, including absolute paths. Its public
        # Node API can select exact TestSpecifications without changing consumer config.
        return [
            "node",
            str(Path(__file__).with_name("vitest-reference.mjs")),
            json.dumps(
                {
                    "path": relative,
                    "config": files[1].relative_to(project_root.resolve()).as_posix()
                    if reference.config
                    else None,
                    "test_name": reference.test_name,
                },
                sort_keys=True,
            ),
        ]
    elif runner == "pytest":
        command = [sys.executable, "-m", "pytest", relative]
        config_flag, selector_flag = "-c", "-k"
    else:
        raise ValueError(f"unsupported existing test runner: {runner}")
    if reference.config is not None:
        command.extend([config_flag, files[1].relative_to(project_root.resolve()).as_posix()])
    if reference.test_name is not None:
        command.extend([selector_flag, reference.test_name])
    return command


def reference_result_error(runner: str, stdout: str, result_path: Path) -> tuple[str, str] | None:
    """Require an observed executed test, separating skipped/empty suites from success."""
    try:
        if runner == "pytest":
            cases = ET.parse(result_path).getroot().iter("testcase")
            count = sum(1 for case in cases if case.find("skipped") is None)
        else:
            result = json.loads(stdout)
            count = (
                result["stats"]["expected"] + result["stats"].get("flaky", 0)
                if runner == "playwright"
                else result["numPassedTests"]
            )
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise ValueError("invalid executed test count")
    except (OSError, ValueError, KeyError, TypeError, ET.ParseError) as error:
        return "journey_test_results_invalid", f"Cannot verify runner results: {error}"
    if count == 0:
        return "journey_no_tests_executed", "Runner completed without executing any selected test"
    return None
