# LiveSpec traceability anchors
# @spec(FR-003)
# @spec(FR-004)

"""Detect Swift Package Manager dependencies and Xcode-only project layouts."""

# @spec FR-003: Package.swift dependency parser
# — .specs/features/019-driver-swift/spec.md#fr-003
# @spec FR-004: Xcode project detection fallback
# — .specs/features/019-driver-swift/spec.md#fr-004

from __future__ import annotations

import re
from pathlib import Path

# `.package(url: "https://example.com/owner/Repo.git", ...)` -> "Repo"
# `.package(url: "https://example.com/owner/Repo", ...)`     -> "Repo"
_PACKAGE_URL_RE = re.compile(
    r"""\.package\(\s*url\s*:\s*["']([^"']+)["']""",
    re.IGNORECASE,
)
# `.package(name: "MyLib", ...)` -> "MyLib"
_PACKAGE_NAME_RE = re.compile(
    r"""\.package\(\s*name\s*:\s*["']([^"']+)["']""",
    re.IGNORECASE,
)


def _read_package_swift(project_root: Path) -> str:
    """Load ``Package.swift`` defensively.

    Args:
        project_root: Path to the project root.

    Returns:
        File contents, or an empty string when the file is missing or unreadable.
    """
    package_swift_path = project_root / "Package.swift"
    if not package_swift_path.is_file():
        return ""
    try:
        return package_swift_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def _name_from_url(url: str) -> str:
    """Extract the trailing repository name from a Swift package URL."""
    last = url.rstrip("/").rsplit("/", 1)[-1]
    if last.endswith(".git"):
        last = last[: -len(".git")]
    return last


def parse_package_dependencies(project_root: str) -> list[str]:
    """Parse ``Package.swift`` and return declared package names.

    Recognises both the URL-based form (``.package(url: ...)``) and the
    explicit-name form (``.package(name: ...)``). Names are returned
    lowercased and de-duplicated, preserving first-seen order.

    Args:
        project_root: Path to the project root.

    Returns:
        Lowercased package names declared as dependencies. Empty when
        ``Package.swift`` is missing, unreadable, or contains no matches.
    """
    contents = _read_package_swift(Path(project_root))
    if not contents:
        return []

    seen: set[str] = set()
    ordered: list[str] = []

    for url_match in _PACKAGE_URL_RE.finditer(contents):
        name = _name_from_url(url_match.group(1)).lower()
        if name and name not in seen:
            seen.add(name)
            ordered.append(name)

    for name_match in _PACKAGE_NAME_RE.finditer(contents):
        name = name_match.group(1).strip().lower()
        if name and name not in seen:
            seen.add(name)
            ordered.append(name)

    return ordered


def has_swift_dependency(project_root: str, name: str) -> bool:
    """Check whether ``name`` is declared as a Swift package dependency.

    Comparison is case-insensitive, matching how Swift package names are
    typically referenced in code regardless of capitalisation.

    Args:
        project_root: Path to the project root.
        name: Dependency name to look up (e.g. ``swift-snapshot-testing``).

    Returns:
        ``True`` when the dependency appears in ``Package.swift``.
    """
    needle = name.strip().lower()
    if not needle:
        return False
    return needle in parse_package_dependencies(project_root)


def has_swift_package(project_root: str) -> bool:
    """Return ``True`` when ``Package.swift`` exists at the project root."""
    return (Path(project_root) / "Package.swift").is_file()


def is_xcode_only_project(project_root: str) -> bool:
    """Detect projects that have an Xcode workspace but no SwiftPM manifest.

    Args:
        project_root: Path to the project root.

    Returns:
        ``True`` when at least one ``*.xcodeproj`` exists and ``Package.swift``
        is absent — this is the case the coverage capability skips with a
        message redirecting the user to ``xcodebuild`` (spec AC-004).
    """
    project_root_path = Path(project_root)
    if (project_root_path / "Package.swift").is_file():
        return False
    return any(project_root_path.glob("*.xcodeproj"))
