"""Scaffold a custom driver YAML for an unsupported stack."""

# Feature 023: driver custom scaffolding & graceful degradation.
# @spec FR-001: livespec spec.driver --new <stack> creates .specs/drivers/<stack>.yaml
# @spec FR-002: Template lives at livespec/drivers/templates/custom-driver-template.yaml
# @spec AC-001: Generated YAML has all 5 sections (detect + 4 capabilities)
# @spec AC-002: Generated YAML passes schema validation
# @spec AC-003: --force absent + file exists -> non-zero, no overwrite
# @spec AC-004: --force overwrites the existing manifest
# @spec AC-005: detect.files pre-filled when stack name is recognized
# @spec EC-001: Hyphenated/dotted stack names sanitized to valid filename
# @spec EC-002: .specs/drivers/ created if missing


from __future__ import annotations

import re
from pathlib import Path

# Pre-fill detect.files patterns by recognized stack slug.
# Used to give scaffolded drivers a sensible starting point (AC-005).
_STACK_DETECT_PATTERNS: dict[str, list[str]] = {
    "elixir": ["mix.exs", "*.ex"],
    "ruby": ["Gemfile", "*.rb"],
    "php": ["composer.json", "*.php"],
    "python": ["pyproject.toml", "setup.py"],
    "node": ["package.json"],
    "typescript": ["tsconfig.json", "package.json"],
    "swift": ["Package.swift"],
    "go": ["go.mod"],
    "rust": ["Cargo.toml"],
    "jvm": ["build.gradle", "build.gradle.kts", "pom.xml"],
}

_TEMPLATE_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "livespec"
    / "drivers"
    / "templates"
    / "custom-driver-template.yaml"
)

# Backward-compat shim: previously a constant string. Now loaded lazily so
# tests/callers that imported `TEMPLATE` keep working.
TEMPLATE = _TEMPLATE_PATH.read_text(encoding="utf-8")


class DriverFileExistsError(FileExistsError):
    """Raised when the scaffold target already exists and ``--force`` is absent."""


def _sanitize_stack_name(stack: str) -> str:
    """Sanitize a stack slug into a safe filename stem.

    Args:
        stack: Raw stack identifier supplied by the caller.

    Returns:
        Lowercased slug with only ``[a-z0-9.-]`` characters and no leading dot.
    """
    cleaned = re.sub(r"[^a-zA-Z0-9.\-]+", "-", stack.strip()).strip("-").lower()
    if cleaned.startswith("."):
        cleaned = cleaned.lstrip(".")
    return cleaned


def _detect_files_yaml(stack: str) -> str:
    """Render the detect.files block for a given stack slug.

    Args:
        stack: Stack slug whose recognized patterns drive pre-fill.

    Returns:
        YAML list body indented under ``detect.files:`` (each line two-space
        indented). Falls back to a commented placeholder when the stack is
        unknown so the resulting YAML is still valid.
    """
    patterns = _STACK_DETECT_PATTERNS.get(stack)
    if patterns:
        # Quote each pattern: YAML treats a leading `*` as an alias reference,
        # which breaks for globs like `*.ex` or `*.rb`.
        return "\n".join(f'    - "{pat}"' for pat in patterns)
    # Unknown stack: emit an empty list with an inline hint as a comment.
    # Schema accepts an empty list; user fills it in.
    return "    []  # e.g. - mix.exs   (top-level globs identify the stack)"


def _render_template(stack: str) -> str:
    """Render the embedded template for a given stack slug.

    Args:
        stack: Sanitized stack slug to embed in the manifest.

    Returns:
        Fully rendered YAML text ready to write to disk.
    """
    template = _TEMPLATE_PATH.read_text(encoding="utf-8")
    return template.format(stack=stack, detect_files=_detect_files_yaml(stack))


def scaffold_custom_driver(
    stack: str,
    *,
    project_root: Path | None = None,
    force: bool = False,
) -> Path:
    """Write ``.specs/drivers/<stack>.yaml`` from the embedded template.

    Args:
        stack: Stack slug to embed in the scaffolded filename and manifest.
        project_root: Repository root where the custom driver directory lives.
        force: Whether to overwrite an existing manifest file.

    Returns:
        Path to the scaffolded manifest file.

    Raises:
        ValueError: ``stack`` is empty or would escape the target directory.
        DriverFileExistsError: The target file exists and ``force`` is ``False``.
    """
    if not stack or "/" in stack or stack.startswith(".") or ".." in stack:
        raise ValueError(f"Invalid stack name: {stack!r}")
    sanitized = _sanitize_stack_name(stack)
    if not sanitized:
        raise ValueError(f"Invalid stack name: {stack!r}")
    root = project_root or Path.cwd()
    target_dir = root / ".specs" / "drivers"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{sanitized}.yaml"
    if target.exists() and not force:
        raise DriverFileExistsError(
            f"Driver {target} already exists. Use --force to overwrite."
        )
    target.write_text(_render_template(sanitized), encoding="utf-8")
    return target
