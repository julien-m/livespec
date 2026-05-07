"""Detect Go module dependencies declared in ``go.mod``."""

# @spec FR-003: go.mod dependency parser
# — .specs/features/020-driver-go/spec.md#fr-003
# @spec AC-009: go.mod parsing uses a dedicated parser (not shell grep).
# — .specs/features/020-driver-go/spec.md#ac-009

from __future__ import annotations

from pathlib import Path


def _read_go_mod(project_root: Path) -> str:
    """Load ``go.mod`` defensively.

    Args:
        project_root: Path to the project root.

    Returns:
        File contents, or an empty string when the file is missing or unreadable.
    """
    go_mod_path = project_root / "go.mod"
    if not go_mod_path.is_file():
        return ""
    try:
        return go_mod_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def _strip_inline_comment(line: str) -> str:
    """Remove a trailing ``// ...`` comment (e.g. ``// indirect``)."""
    idx = line.find("//")
    if idx >= 0:
        line = line[:idx]
    return line.strip()


def parse_go_module(project_root: str) -> str | None:
    """Return the module path declared in ``go.mod``.

    Recognises the canonical ``module <path>`` declaration. Quoted paths
    (``module "example.com/foo"``) are accepted as well.

    Args:
        project_root: Path to the project root.

    Returns:
        The module path string, or ``None`` when ``go.mod`` is missing,
        unreadable, or does not declare a module.
    """
    contents = _read_go_mod(Path(project_root))
    if not contents:
        return None

    for raw_line in contents.splitlines():
        line = _strip_inline_comment(raw_line)
        if not line.startswith("module"):
            continue
        # Skip the leading "module" keyword and surrounding whitespace.
        rest = line[len("module") :].strip()
        if not rest:
            continue
        # `module "path"` form.
        if rest.startswith('"') and rest.endswith('"') and len(rest) >= 2:
            return rest[1:-1]
        return rest

    return None


def parse_go_dependencies(project_root: str) -> list[str]:
    """Parse ``go.mod`` and return the declared ``require`` module paths.

    Recognises both the single-line ``require <path> <version>`` form and the
    multi-line ``require ( ... )`` block. Trailing ``// indirect`` markers and
    other inline comments are stripped. Module paths are returned lowercased
    and de-duplicated, preserving first-seen order.

    Args:
        project_root: Path to the project root.

    Returns:
        Lowercased module paths declared as dependencies. Empty when ``go.mod``
        is missing, unreadable, or contains no ``require`` entries.
    """
    contents = _read_go_mod(Path(project_root))
    if not contents:
        return []

    seen: set[str] = set()
    ordered: list[str] = []
    in_block = False

    def _record(path: str) -> None:
        normalised = path.strip().lower()
        if normalised and normalised not in seen:
            seen.add(normalised)
            ordered.append(normalised)

    for raw_line in contents.splitlines():
        line = _strip_inline_comment(raw_line)
        if not line:
            continue

        if in_block:
            if line == ")":
                in_block = False
                continue
            tokens = line.split()
            if tokens:
                _record(tokens[0])
            continue

        if line.startswith("require"):
            rest = line[len("require") :].strip()
            if rest == "(":
                in_block = True
                continue
            if rest.startswith("("):
                # `require ( path version` (rare but legal once the parenthesis
                # opens on the same logical line as the keyword).
                in_block = True
                rest = rest[1:].strip()
                if rest:
                    tokens = rest.split()
                    _record(tokens[0])
                continue
            if not rest:
                # Malformed but harmless — skip.
                continue
            tokens = rest.split()
            _record(tokens[0])

    return ordered


def has_go_dependency(project_root: str, name: str) -> bool:
    """Check whether ``name`` is declared in any ``require`` entry of ``go.mod``.

    The match is case-insensitive and substring-based against the module path,
    so callers may pass either the trailing module name (``gopter``) or the
    full path (``github.com/leanovate/gopter``).

    Args:
        project_root: Path to the project root.
        name: Dependency identifier to look up.

    Returns:
        ``True`` when at least one ``require`` entry contains ``name`` (case-
        insensitive).
    """
    needle = name.strip().lower()
    if not needle:
        return False
    return any(needle in dep for dep in parse_go_dependencies(project_root))


def has_go_module(project_root: str) -> bool:
    """Return ``True`` when ``go.mod`` exists at the project root."""
    return (Path(project_root) / "go.mod").is_file()
