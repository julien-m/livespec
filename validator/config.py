"""Configuration loading and file type resolution."""

from __future__ import annotations

from dataclasses import dataclass, field
from fnmatch import fnmatch
from pathlib import Path
from typing import Literal

import yaml


ALL_TYPES = [
    "spec", "plan", "implementation", "roadmap", "changelog",
    "stack", "preflight", "progress", "constitution", "project",
]

DEFAULT_EXCLUSIONS = [
    "README.md",
    "preflight-report.md",
    "spec-system.md",
    "stacks/decisions/*.md",
    "features/*/logs/*.md",
    "features/*/checks/*.md",
    "features/*/baselines/*",
    "archive/*.md",
    "archive/**/*.md",
    "design/**/*.md",
    "testing/*.md",
    "hooks/*.md",
]


@dataclass
class ValidatorConfig:
    """Validator configuration, loaded from validator.yml or defaults."""

    block_on: Literal["error", "warning"] = "error"
    validate_types: list[str] = field(default_factory=lambda: list(ALL_TYPES))
    exclude: list[str] = field(default_factory=lambda: list(DEFAULT_EXCLUSIONS))


def load_config(specs_root: Path) -> ValidatorConfig:
    """Load validator.yml from specs_root if present, else return defaults."""
    config_path = specs_root / "validator.yml"

    if not config_path.exists():
        return ValidatorConfig()

    with open(config_path) as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        return ValidatorConfig()

    return ValidatorConfig(
        block_on=data.get("block_on", "error"),
        validate_types=data.get("validate", list(ALL_TYPES)),
        exclude=data.get("exclude", list(DEFAULT_EXCLUSIONS)),
    )


def is_excluded(rel_path: str, config: ValidatorConfig) -> bool:
    """Check if a relative path matches any exclusion pattern."""
    for pattern in config.exclude:
        if fnmatch(rel_path, pattern):
            return True
    return False


def resolve_file_type(path: Path, specs_root: Path) -> str:
    """Determine the file type from its path relative to specs_root.

    Returns one of: spec, plan, implementation, roadmap, changelog,
    stack, preflight, progress, constitution, project, unknown.
    """
    try:
        rel = path.relative_to(specs_root)
    except ValueError:
        return "unknown"

    parts = rel.parts

    # Feature files: features/<name>/<type>.md
    if parts[0] == "features" and len(parts) >= 3:
        return parts[2].removesuffix(".md")

    # Stack files: stacks/_default.md
    if parts[0] == "stacks" and parts[-1] == "_default.md":
        return "stack"

    # Root-level files
    if len(parts) == 1:
        return parts[0].removesuffix(".md")

    return "unknown"
