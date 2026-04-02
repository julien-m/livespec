"""Validation engine — orchestrates the full pipeline per file."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import ValidationError

from .config import ValidatorConfig, is_excluded, load_config, resolve_file_type
from .parser import parse_file
from .rules import validate_by_type, validate_sections
from .schemas import get_schema


@dataclass
class ValidationMessage:
    """A single validation error or warning."""

    category: str  # "frontmatter", "section", "rule"
    message: str


@dataclass
class FileResult:
    """Validation result for a single file."""

    path: Path
    file_type: str = "unknown"
    errors: list[ValidationMessage] = field(default_factory=list)
    warnings: list[ValidationMessage] = field(default_factory=list)
    score: int = 100

    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0

    @property
    def has_warnings(self) -> bool:
        return len(self.warnings) > 0


def validate_file(path: Path, specs_root: Path, config: ValidatorConfig) -> FileResult:
    """Run the full validation pipeline on a single file."""
    file_type = resolve_file_type(path, specs_root)
    result = FileResult(path=path, file_type=file_type)

    # Skip unknown types
    if file_type == "unknown":
        return result

    # Skip types not in config.validate_types
    if file_type not in config.validate_types:
        return result

    # Parse file
    try:
        parsed = parse_file(path)
    except Exception as e:
        result.errors.append(ValidationMessage("frontmatter", f"Parse error: {e}"))
        result.score = 0
        return result

    # 1. Validate frontmatter (Pydantic)
    schema = get_schema(file_type)
    if schema is not None:
        if not parsed.metadata:
            result.errors.append(ValidationMessage("frontmatter", "Missing frontmatter"))
        else:
            try:
                schema(**parsed.metadata)
            except ValidationError as e:
                for err in e.errors():
                    field_name = ".".join(str(loc) for loc in err["loc"])
                    result.errors.append(
                        ValidationMessage("frontmatter", f"{field_name}: {err['msg']}")
                    )

    # 2. Validate sections (AST headings)
    section_errors, section_warnings = validate_sections(parsed.headings, file_type)
    for msg in section_errors:
        result.errors.append(ValidationMessage("section", msg))
    for msg in section_warnings:
        result.warnings.append(ValidationMessage("section", msg))

    # 3. Validate type-specific rules
    rule_errors = validate_by_type(parsed.content, file_type, parsed.code_blocks)
    for msg in rule_errors:
        result.errors.append(ValidationMessage("rule", msg))

    # 4. Compute score (display only)
    result.score = max(0, 100 - len(result.errors) * 20 - len(result.warnings) * 5)

    return result


def _get_staged_files(specs_root: Path) -> list[Path]:
    """Get list of staged .specs/*.md files from git."""
    try:
        output = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
            capture_output=True,
            text=True,
            cwd=specs_root.parent,
            check=True,
        )
        files = []
        specs_rel = specs_root.name
        for line in output.stdout.strip().splitlines():
            if line.startswith(f"{specs_rel}/") and line.endswith(".md"):
                files.append(specs_root.parent / line)
        return files
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []


def collect_files(
    specs_root: Path,
    config: ValidatorConfig,
    paths: list[Path] | None = None,
    staged_only: bool = False,
) -> tuple[list[Path], list[str]]:
    """Collect files to validate, applying exclusions.

    Returns (files_to_validate, excluded_paths).
    """
    if staged_only:
        candidates = _get_staged_files(specs_root)
    elif paths:
        candidates = []
        for p in paths:
            if p.is_file():
                candidates.append(p)
            elif p.is_dir():
                candidates.extend(sorted(p.rglob("*.md")))
    else:
        candidates = sorted(specs_root.rglob("*.md"))

    files: list[Path] = []
    excluded: list[str] = []

    for f in candidates:
        try:
            rel = str(f.relative_to(specs_root))
        except ValueError:
            continue

        if is_excluded(rel, config):
            excluded.append(rel)
        else:
            files.append(f)

    return files, excluded


def validate_all(
    specs_root: Path,
    config: ValidatorConfig | None = None,
    paths: list[Path] | None = None,
    staged_only: bool = False,
) -> tuple[list[FileResult], list[str]]:
    """Validate all matching files. Returns (results, excluded_paths)."""
    if config is None:
        config = load_config(specs_root)

    files, excluded = collect_files(specs_root, config, paths, staged_only)

    results = [validate_file(f, specs_root, config) for f in files]

    return results, excluded
