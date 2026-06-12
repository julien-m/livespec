# LiveSpec traceability anchors
# @spec(FR-001)

"""Tests for conventions gates schema loading and generation."""

from __future__ import annotations

from pathlib import Path

import pytest

from validator.conventions_gates import (
    ConventionsGates,
    generate_conventions_gates,
    load_conventions_gates,
)


def _project_with_specs(tmp_path: Path, stack: str) -> Path:
    specs = tmp_path / ".specs"
    (specs / "stacks").mkdir(parents=True)
    (specs / "constitution.md").write_text(
        "# Constitution\n\n- Enforce Python and TypeScript conventions.\n",
        encoding="utf-8",
    )
    (specs / "stacks" / "_default.md").write_text(stack, encoding="utf-8")
    return tmp_path


def test_generate_gates_uses_two_level_thresholds_and_source_hash(tmp_path: Path) -> None:
    project_root = _project_with_specs(tmp_path, "# Stack\n\nPython CLI, TypeScript React\n")

    path = generate_conventions_gates(project_root)

    gates = load_conventions_gates(path)
    assert path == project_root / ".specs" / "conventions-gates.yaml"
    assert gates.builtin.max_file_lines.target == 400
    assert gates.builtin.max_file_lines.limit == 500
    assert gates.builtin.max_function_lines.target == 30
    assert gates.builtin.max_function_lines.limit == 60
    assert gates.generated_from.constitution == ".specs/constitution.md"
    assert len(gates.generated_from.constitution_sha256) == 64
    assert {command.id for command in gates.commands.lint} == {"ruff", "eslint"}


def test_load_gates_rejects_invalid_threshold_order(tmp_path: Path) -> None:
    gates_path = tmp_path / "gates.yaml"
    gates_path.write_text(
        """
schema_version: 1
generated_from:
  constitution: .specs/constitution.md
  constitution_sha256: 0000000000000000000000000000000000000000000000000000000000000000
  stack: .specs/stacks/_default.md
commands:
  lint: []
builtin:
  max_file_lines: {target: 500, limit: 400}
  max_function_lines: {target: 30, limit: 60}
coverage:
  python: full
scope: repo
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match=r"target.*limit"):
        load_conventions_gates(gates_path)


def test_conventions_gates_model_round_trips_minimal_yaml() -> None:
    gates = ConventionsGates.model_validate(
        {
            "schema_version": 1,
            "generated_from": {
                "constitution": ".specs/constitution.md",
                "constitution_sha256": "0" * 64,
                "stack": ".specs/stacks/_default.md",
            },
            "commands": {
                "lint": [
                    {
                        "id": "ruff",
                        "run": "ruff check . --output-format json",
                        "version": "0.6.0",
                        "config": "pyproject.toml",
                    }
                ]
            },
            "builtin": {
                "max_file_lines": {"target": 400, "limit": 500},
                "max_function_lines": {"target": 30, "limit": 60},
                "suppression_directives": {"budget": 0, "whitelist": []},
            },
            "coverage": {"python": "full", "typescript": "full"},
            "exclusions": [".specs/**"],
            "scope": "repo",
        }
    )

    assert gates.commands.lint[0].id == "ruff"
    assert gates.builtin.suppression_directives.budget == 0


def test_conventions_gates_v1_rejects_delegate_and_wiring_fields() -> None:
    payload = {
        "schema_version": 1,
        "generated_from": {
            "constitution": ".specs/constitution.md",
            "constitution_sha256": "0" * 64,
            "stack": ".specs/stacks/_default.md",
        },
        "commands": {
            "lint": [
                {
                    "id": "ruff",
                    "run": "ruff check . --output-format json",
                    "wiring": [{"kind": "covers_rule", "rule": "builtin.max_file_lines"}],
                }
            ]
        },
        "builtin": {
            "max_file_lines": {"target": 400, "limit": 500, "delegate_to": "ruff"},
            "max_function_lines": {"target": 30, "limit": 60},
        },
        "scope": "repo",
    }

    with pytest.raises(ValueError, match="Extra inputs are not permitted"):
        ConventionsGates.model_validate(payload)
