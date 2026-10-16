"""Strict declarations prevent accidental timeout inflation before execution."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from validator.test_budgets import DEFAULT_TEST_SECONDS, load_budget_policy


def _policy(root: Path, exceptions: list[dict[str, object]]) -> None:
    path = root / ".specs/testing/test-budgets.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump({"schema_version": 1, "exceptions": exceptions}))


# @spec AC-004: Strict prior scoped exceptions
# — .specs/features/095-test-time-budgets/spec.md#ac-004
def test_exact_prior_exception_preserves_other_limits(tmp_path: Path) -> None:
    _policy(
        tmp_path,
        [
            {
                "id": "capacity",
                "command": ["cargo", "test"],
                "category": "benchmark",
                "reason": "Required capacity measurement",
                "command_seconds": 600,
            }
        ],
    )
    policy = load_budget_policy(tmp_path)
    assert DEFAULT_TEST_SECONDS == {"unit": 2, "integration": 10, "acceptance": 30}
    with pytest.raises(ValueError, match="declared command budget"):
        policy.command_limit(["pytest"], 601)
    assert (
        policy.command_limit(["cargo", "test"]),
        policy.command_limit(["cargo", "test", "--lib"]),
        policy.command_limit(["pytest"], 0.2),
    ) == (600, 300, 0.2)


@pytest.mark.parametrize(
    "change",
    [
        {"command_seconds": 601},
        {"command_seconds": True},
        {"command_seconds": float("inf")},
        {"reason": " "},
        {"unexpected": 1},
        {"test": "x", "test_seconds": 400, "command_seconds": 300},
    ],
)
def test_invalid_declarations_fail_before_spawn(tmp_path: Path, change: dict[str, object]) -> None:
    _policy(
        tmp_path,
        [
            {
                "id": "a",
                "command": ["pytest"],
                "category": "benchmark",
                "reason": "capacity",
                "command_seconds": 600,
                **change,
            }
        ],
    )
    with pytest.raises(ValueError):
        load_budget_policy(tmp_path)


def test_duplicate_yaml_and_conflicting_scopes_are_refused(tmp_path: Path) -> None:
    path = tmp_path / ".specs/testing/test-budgets.yaml"
    path.parent.mkdir(parents=True)
    path.write_text("schema_version: 1\nschema_version: 1\n")
    with pytest.raises(ValueError, match="duplicate"):
        load_budget_policy(tmp_path)
    item: dict[str, object] = {
        "id": "a",
        "command": ["pytest"],
        "category": "generation",
        "reason": "generator",
        "command_seconds": 500,
    }
    _policy(tmp_path, [item, {**item, "id": "b"}])
    with pytest.raises(ValueError, match="duplicate"):
        load_budget_policy(tmp_path)


def test_test_exception_needs_sufficient_parent_declaration(tmp_path: Path) -> None:
    _policy(
        tmp_path,
        [
            {
                "id": "large",
                "command": ["pytest"],
                "test": "test_a.py::test_big",
                "test_seconds": 400,
                "category": "benchmark",
                "reason": "capacity",
                "command_seconds": 600,
            }
        ],
    )
    with pytest.raises(ValueError, match="command-wide"):
        load_budget_policy(tmp_path).command_limit(["pytest"])
