# LiveSpec traceability anchors
# @spec(FR-001)

"""Conventions gates schema, loader, and deterministic generator."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal, cast

import yaml  # type: ignore[import-untyped]  # PyYAML is a runtime dependency without stubs.
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .visual_evidence import sha256_file

GATES_RELATIVE_PATH = Path(".specs/conventions-gates.yaml")
DEFAULT_SOURCE_EXCLUSIONS = (
    ".specs/**",
    ".git/**",
    ".mimocode/**",
    ".mypy_cache/**",
    ".pytest_cache/**",
    ".ruff_cache/**",
    ".venv/**",
    "build/**",
    "coverage/**",
    "dist/**",
    "node_modules/**",
    "playwright-report/**",
    "**/__pycache__/**",
    "**/Generated/**",
    "**/node_modules/**",
)


class GatesBaseModel(BaseModel):
    """Strict frozen base model for gates YAML."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class GeneratedFrom(GatesBaseModel):
    """Source metadata used to detect stale gates."""

    constitution: str
    constitution_sha256: str
    stack: str

    @field_validator("constitution_sha256", mode="before")
    @classmethod
    def normalize_sha256(cls, value: object) -> object:
        """Normalize YAML's unquoted all-zero SHA integer edge case."""
        return "0" * 64 if value == 0 else value

    @field_validator("constitution_sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        """Validate SHA-256 shape."""
        if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
            raise ValueError("constitution_sha256 must be 64 lowercase hex chars")
        return value


class GateCommand(GatesBaseModel):
    """One external command declared by the gates file."""

    id: str
    run: str
    version: str | None = None
    config: str | None = None


class CommandGroups(GatesBaseModel):
    """Groups of commands that verify conventions."""

    lint: list[GateCommand] = Field(default_factory=list)
    format: list[GateCommand] = Field(default_factory=list)
    typecheck: list[GateCommand] = Field(default_factory=list)


class ThresholdRule(GatesBaseModel):
    """Two-level threshold: target warns, limit errors."""

    target: int
    limit: int

    @model_validator(mode="after")
    def validate_order(self) -> ThresholdRule:
        """Ensure target is not stricter than limit."""
        if self.target > self.limit:
            raise ValueError("target must be <= limit")
        return self


class SuppressionDirectives(GatesBaseModel):
    """Inline suppression budget."""

    budget: int = 0
    whitelist: list[str] = Field(default_factory=list)


class TokenScale(GatesBaseModel):
    """Allowed numeric design-token scale."""

    scale: list[int] = Field(default_factory=lambda: [2, 4, 8, 12, 16, 24, 32, 40, 48, 64, 80])
    properties: list[str] = Field(default_factory=lambda: ["padding", "margin", "spacing"])


class BuiltinRules(GatesBaseModel):
    """Builtin deterministic checks not always expressed by linters."""

    max_file_lines: ThresholdRule = Field(
        default_factory=lambda: ThresholdRule(target=400, limit=500)
    )
    max_function_lines: ThresholdRule = Field(
        default_factory=lambda: ThresholdRule(target=30, limit=60)
    )
    file_header: dict[str, str | None] = Field(default_factory=dict)
    doc_coverage: dict[str, bool] = Field(default_factory=lambda: {"require_public_api": True})
    token_scale: TokenScale = Field(default_factory=TokenScale)
    suppression_directives: SuppressionDirectives = Field(default_factory=SuppressionDirectives)
    import_rules: list[dict[str, dict[str, str]]] = Field(default_factory=list)


class ConventionsGates(GatesBaseModel):
    """Root `.specs/conventions-gates.yaml` model."""

    schema_version: Literal[1]
    generated_from: GeneratedFrom
    commands: CommandGroups = Field(default_factory=CommandGroups)
    builtin: BuiltinRules = Field(default_factory=BuiltinRules)
    coverage: dict[str, str] = Field(default_factory=dict)
    exclusions: list[str] = Field(default_factory=lambda: list(DEFAULT_SOURCE_EXCLUSIONS))
    scope: Literal["repo"] = "repo"


def load_conventions_gates(path: Path) -> ConventionsGates:
    """Load and validate a conventions gates YAML file.

    Args:
        path: Gates YAML path.

    Returns:
        Validated gates model.

    Raises:
        ValueError: If YAML is unreadable, malformed, or schema-invalid.
    """
    if path.is_dir():
        path = gates_path(path)
    try:
        raw: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ValueError(f"invalid gates yaml: {path}") from exc
    if not isinstance(raw, dict):
        raise ValueError("gates root must be a mapping")
    return ConventionsGates.model_validate(raw)


def generate_conventions_gates(project_root: Path, *, force: bool = False) -> Path:
    """Generate `.specs/conventions-gates.yaml` from project sources.

    Args:
        project_root: Project root containing `.specs/constitution.md`.
        force: Overwrite an existing gates file.

    Returns:
        Written gates path.

    Raises:
        FileExistsError: If the gates file exists and `force` is false.
        FileNotFoundError: If source spec files are absent.
    """
    gates_path = project_root / GATES_RELATIVE_PATH
    if gates_path.exists() and not force:
        raise FileExistsError(gates_path)
    constitution = project_root / ".specs" / "constitution.md"
    stack = project_root / ".specs" / "stacks" / "_default.md"
    if not constitution.is_file() or not stack.is_file():
        raise FileNotFoundError(".specs/constitution.md or .specs/stacks/_default.md missing")
    gates = _build_default_gates(project_root, constitution, stack)
    gates_path.parent.mkdir(parents=True, exist_ok=True)
    gates_path.write_text(_dump_yaml(gates.model_dump(exclude_none=True)), encoding="utf-8")
    return gates_path


def gates_path(project_root: Path) -> Path:
    """Return the project gates file path."""
    return project_root / GATES_RELATIVE_PATH


def _build_default_gates(project_root: Path, constitution: Path, stack: Path) -> ConventionsGates:
    stack_text = stack.read_text(encoding="utf-8").lower()
    commands = _commands_for_stack(stack_text)
    coverage = _coverage_for_commands(commands)
    return ConventionsGates(
        schema_version=1,
        generated_from=GeneratedFrom(
            constitution=".specs/constitution.md",
            constitution_sha256=sha256_file(constitution),
            stack=".specs/stacks/_default.md",
        ),
        commands=CommandGroups(lint=commands),
        builtin=BuiltinRules(
            max_file_lines=ThresholdRule(target=400, limit=500),
            max_function_lines=ThresholdRule(target=30, limit=60),
            file_header={"swift": r"^//\n//  [^\n]+\.swift", "python": None},
        ),
        coverage=coverage,
        exclusions=list(DEFAULT_SOURCE_EXCLUSIONS),
        scope="repo",
    )


def _commands_for_stack(stack_text: str) -> list[GateCommand]:
    commands: list[GateCommand] = []
    if "python" in stack_text:
        commands.append(
            GateCommand(
                id="ruff",
                run="ruff check . --output-format json",
                config="pyproject.toml",
            )
        )
    if any(marker in stack_text for marker in ("typescript", "react", "javascript", "node")):
        commands.append(GateCommand(id="eslint", run="eslint . --format json"))
    if "swift" in stack_text:
        commands.append(
            GateCommand(
                id="swiftlint",
                run="swiftlint lint --strict --quiet --reporter json",
                config=".swiftlint.yml",
            )
        )
    return commands


def _coverage_for_commands(commands: list[GateCommand]) -> dict[str, str]:
    coverage: dict[str, str] = {}
    for command in commands:
        if command.id == "ruff":
            coverage["python"] = "full"
        elif command.id == "eslint":
            coverage["typescript"] = "full"
            coverage["react"] = "full"
        elif command.id == "swiftlint":
            coverage["swift"] = "full"
    if not coverage:
        coverage["fallback"] = "partial"
    return coverage


def _dump_yaml(payload: dict[str, Any]) -> str:
    return cast(str, yaml.safe_dump(payload, sort_keys=False, allow_unicode=False))
