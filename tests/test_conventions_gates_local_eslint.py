"""Generated eslint gates run the project-local binary (061 FR-001).

Regression for the Handy report: ``livespec conventions gates init`` wrote
``run: eslint . --format json``, which fails with ``eslint: command not found`` when
eslint is installed only in ``node_modules/.bin``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from validator.conventions_gates import generate_conventions_gates, load_conventions_gates
from validator.conventions_linter_runner import collect_linter_violations


def _project(root: Path) -> Path:
    (root / ".specs/stacks").mkdir(parents=True)
    (root / ".specs/constitution.md").write_text("# Constitution\n\nKeep it simple.\n")
    (root / ".specs/stacks/_default.md").write_text("# Stack\n\n- TypeScript and React\n")
    return root


def _eslint_command(root: Path) -> str:
    gates = load_conventions_gates(generate_conventions_gates(root, force=True))
    return next(command.run for command in gates.commands.lint if command.id == "eslint")


# @spec FR-001: Generated lint commands resolve the project-local eslint
#   — .specs/features/061-conventions-gates-engine/spec.md#fr-001
def test_local_eslint_binary_runs_without_a_global_install(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _project(tmp_path)
    binary = root / "node_modules/.bin/eslint"
    binary.parent.mkdir(parents=True)
    binary.write_text("#!/bin/sh\necho '[]'\n")
    binary.chmod(0o755)
    assert _eslint_command(root) == "node_modules/.bin/eslint . --format json"
    monkeypatch.setenv("PATH", "/usr/bin:/bin")
    gates = load_conventions_gates(root / ".specs/conventions-gates.yaml")
    assert collect_linter_violations(root, gates) == []


def test_declared_but_uninstalled_eslint_still_targets_the_local_binary(tmp_path: Path) -> None:
    root = _project(tmp_path)
    (root / "package.json").write_text(json.dumps({"devDependencies": {"eslint": "^9.0.0"}}))
    assert _eslint_command(root) == "node_modules/.bin/eslint . --format json"


def test_without_a_local_eslint_the_global_command_is_kept(tmp_path: Path) -> None:
    root = _project(tmp_path)
    (root / "package.json").write_text(json.dumps({"devDependencies": {"vite": "^7.0.0"}}))
    assert _eslint_command(root) == "eslint . --format json"
