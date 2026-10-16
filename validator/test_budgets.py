"""Strict, pre-execution policy for bounded validation."""

# @spec FR-004: Scoped declared exceptions — .specs/features/095-test-time-budgets/spec.md#fr-004
from __future__ import annotations

import math
from pathlib import Path
from typing import Literal, cast

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Category = Literal["unit", "integration", "acceptance", "benchmark", "generation"]
DEFAULT_TEST_SECONDS = {"unit": 2.0, "integration": 10.0, "acceptance": 30.0}
DEFAULT_COMMAND_SECONDS = 300.0


class BudgetException(BaseModel):
    """One exact command or test scope declared before execution."""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
    id: str = Field(min_length=1)
    command: tuple[str, ...]
    test: str | None = None
    category: Category
    reason: str = Field(min_length=1)
    command_seconds: float
    test_seconds: float | None = None

    @field_validator("id", "reason", "test")
    @classmethod
    def nonblank(cls, value: str | None) -> str | None:
        """Refuse empty scopes and justifications."""
        if value is not None and not value.strip():
            raise ValueError("exception identity, reason and test must not be blank")
        return value

    @field_validator("command", mode="before")
    @classmethod
    def argv(cls, value: object) -> tuple[str, ...]:
        """YAML argv is a nonempty exact token list, never a wildcard scope."""
        if not isinstance(value, (list, tuple)):
            raise ValueError("command must be an exact argv list")
        items = cast("list[object]", value)
        if not items or any(not isinstance(x, str) or not x for x in items):
            raise ValueError("command tokens must be nonempty strings")
        return tuple(cast("list[str]", items))

    @field_validator("command_seconds", "test_seconds", mode="before")
    @classmethod
    def duration(cls, value: object) -> float | None:
        """All declared durations are finite, positive and at most ten minutes."""
        if value is None:
            return None
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("duration must be a number")
        seconds = float(value)
        if not math.isfinite(seconds) or not 0 < seconds <= 600:
            raise ValueError("duration must be positive and at most 600 seconds")
        return seconds

    @model_validator(mode="after")
    def consistent(self) -> BudgetException:
        """Test exceptions require an explicit compatible enclosing maximum."""
        if (self.test is None) != (self.test_seconds is None):
            raise ValueError("test and test_seconds must be declared together")
        if self.test_seconds is not None and self.test_seconds > self.command_seconds:
            raise ValueError("test_seconds cannot exceed command_seconds")
        return self


class BudgetPolicy(BaseModel):
    """Immutable policy loaded once for the entire managed invocation."""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
    schema_version: Literal[1] = 1
    exceptions: tuple[BudgetException, ...] = ()

    @model_validator(mode="after")
    def unique(self) -> BudgetPolicy:
        """Ambiguous ids or exact scopes are refused before spawning."""
        ids = [item.id for item in self.exceptions]
        scopes = [(item.command, item.test) for item in self.exceptions]
        if len(ids) != len(set(ids)) or len(scopes) != len(set(scopes)):
            raise ValueError("duplicate exception id or command/test scope")
        return self

    def matching(self, argv: list[str], test: str | None = None) -> BudgetException | None:
        """Match the complete original argv and optional exact collected identity."""
        return next(
            (e for e in self.exceptions if e.command == tuple(argv) and e.test == test), None
        )

    def command_limit(self, argv: list[str], timeout: float | None = None) -> float:
        """Existing timeout arguments may tighten but never enlarge the declared cap."""
        declared = self.matching(argv)
        maximum = declared.command_seconds if declared else DEFAULT_COMMAND_SECONDS
        if timeout is not None and (not math.isfinite(timeout) or not 0 < timeout <= maximum):
            raise ValueError(f"timeout must be positive and <= declared command budget {maximum}s")
        for item in self.exceptions:
            if item.command == tuple(argv) and item.test_seconds and item.test_seconds > maximum:
                raise ValueError("test exception requires a sufficient command-wide declaration")
        return timeout if timeout is not None else maximum

    def frozen(self, argv: list[str], command_seconds: float) -> dict[str, object]:
        """Transfer only the relevant immutable declarations to trusted child hooks."""
        return {
            "command_seconds": command_seconds,
            "defaults": DEFAULT_TEST_SECONDS,
            "exceptions": [e.model_dump() for e in self.exceptions if e.command == tuple(argv)],
        }


class _UniqueLoader(yaml.SafeLoader):
    """YAML loader refusing duplicate keys instead of silently replacing them."""


def _mapping(loader: _UniqueLoader, node: yaml.MappingNode) -> dict[object, object]:
    result: dict[object, object] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node)
        if key in result:
            raise ValueError(f"duplicate policy key: {key}")
        result[key] = loader.construct_object(value_node)
    return result


_UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _mapping)


def load_budget_policy(root: Path) -> BudgetPolicy:
    """Validate the whole active policy before any managed preparation starts."""
    path = root / ".specs/testing/test-budgets.yaml"
    if not path.exists():
        return BudgetPolicy()
    try:
        raw = yaml.load(path.read_text(), Loader=_UniqueLoader)
        if not isinstance(raw, dict):
            raise ValueError("expected a policy mapping")
        data = cast("dict[str, object]", raw)
        if "schema_version" not in data or type(data["schema_version"]) is not int:
            raise ValueError("schema_version: 1 is required")
        exceptions = data.get("exceptions", [])
        if not isinstance(exceptions, list):
            raise ValueError("exceptions must be a list")
        data["exceptions"] = tuple(BudgetException.model_validate(e) for e in exceptions)
        return BudgetPolicy.model_validate(data)
    except (ValueError, yaml.YAMLError) as exc:
        raise ValueError(f"{path}: invalid test budget policy: {exc}") from exc
