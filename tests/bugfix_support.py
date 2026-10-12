"""Temporary git projects and real runner captures for bugfix lane tests (feature 084)."""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from typer.testing import CliRunner, Result

from validator.cli import app

FEATURE = "001-calc"
SPEC = """# Feature Spec: Calc

- **Status:** Implemented

## Acceptance Criteria

### AC-001

Given two numbers, add returns their sum.

### AC-002

Given two numbers, sub returns their difference.

## Functional Requirements

- **FR-001:** Provide add and sub. **Maps to:** AC-001, AC-002.
"""
BUGGY = "def add(a, b):\n    return a - b\n\n\ndef sub(a, b):\n    return a - b\n"
FIXED = "def add(a, b):\n    return a + b\n\n\ndef sub(a, b):\n    return a - b\n"
TEST = "from calc import add\n\n\ndef test_add():\n    assert add(2, 3) == 5\n"


def git(root: Path, *args: str) -> str:
    """Run git in the temporary project and return stdout."""
    return subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, text=True, check=True
    ).stdout


@dataclass
class BugfixProject:
    """A committed temporary project with one implemented feature and a buggy module."""

    root: Path

    @property
    def feature_dir(self) -> Path:
        """Return the owner feature directory."""
        return self.root / ".specs" / "features" / FEATURE

    def write(self, relative: str, text: str) -> None:
        """Write a project file, creating parents."""
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def run(self, *args: str) -> Result:
        """Invoke the real CLI from the project root."""
        return CliRunner().invoke(app, list(args), catch_exceptions=False)

    def capture(self, expect: str, test: str = "tests/test_calc.py") -> tuple[int, str]:
        """Capture a real pytest run; return the exit code and receipt path."""
        result = self.run(
            "bugfix",
            "capture",
            "--feature",
            FEATURE,
            "--expect",
            expect,
            "--command",
            f"{sys.executable} -m pytest -q -p no:cacheprovider {test}",
        )
        receipt = next(
            line.split(": ", 1)[1]
            for line in result.output.splitlines()
            if line.startswith("Receipt")
        )
        return result.exit_code, receipt


def make_project(tmp_path: Path, *, nested: bool = False) -> BugfixProject:
    """Create and commit the project: spec, implementation map, buggy module, no test yet.

    With ``nested`` the repository starts one level above the project root.
    """
    project = BugfixProject(tmp_path / "repo" / "project" if nested else tmp_path / "project")
    project.root.mkdir(parents=True)
    repository = project.root.parent if nested else project.root
    project.write(f".specs/features/{FEATURE}/spec.md", SPEC)
    project.write(f".specs/features/{FEATURE}/implementation.md", "# Implementation\n")
    project.write(f".specs/features/{FEATURE}/changelog.md", "# Changelog\n")
    project.write("calc.py", BUGGY)
    project.write("pyproject.toml", "[tool.pytest.ini_options]\npythonpath = ['.']\n")
    project.write(".gitignore", ".specs/.execution/\n__pycache__/\n")
    git(repository, "init", "-q")
    git(repository, "config", "user.email", "t@example.invalid")
    git(repository, "config", "user.name", "t")
    git(repository, "add", "-A")
    git(repository, "commit", "-qm", "base")
    return project
