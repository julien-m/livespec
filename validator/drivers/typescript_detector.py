"""Detect the TypeScript/JavaScript test runner and package manager."""

# @spec FR-002: Test runner detection (vitest > jest)
# — .specs/features/018-driver-typescript-javascript/spec.md#fr-002
# @spec FR-004: Package manager detection from lockfile presence
# — .specs/features/018-driver-typescript-javascript/spec.md#fr-004

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

_VITEST_CONFIG_NAMES = (
    "vitest.config.ts",
    "vitest.config.js",
    "vitest.config.mjs",
    "vitest.config.cjs",
)
_JEST_CONFIG_NAMES = (
    "jest.config.ts",
    "jest.config.js",
    "jest.config.mjs",
    "jest.config.cjs",
    "jest.config.json",
)
# Order matters: bun before pnpm before yarn before npm so the most specific
# lockfile wins when several coexist (e.g. migration in progress).
_LOCKFILE_TO_PACKAGE_MANAGER: tuple[tuple[str, str], ...] = (
    ("bun.lockb", "bun"),
    ("pnpm-lock.yaml", "pnpm"),
    ("yarn.lock", "yarn"),
    ("package-lock.json", "npm"),
)


def _read_package_json(project_root: Path) -> dict[str, Any]:
    """Load ``package.json`` from ``project_root`` defensively.

    Args:
        project_root: Path to the project root.

    Returns:
        Parsed ``package.json`` mapping, or an empty mapping when the file is
        missing or unreadable.
    """
    package_json_path = project_root / "package.json"
    if not package_json_path.is_file():
        return {}

    try:
        with package_json_path.open(encoding="utf-8") as package_json_file:
            data = json.load(package_json_file)
    except (OSError, json.JSONDecodeError):
        return {}

    if not isinstance(data, dict):
        return {}

    return cast(dict[str, Any], data)


def detect_test_runner(project_root: str) -> str:
    """Decide which test runner the driver should invoke.

    Resolution order, per AC-002:
    1. ``vitest.config.{ts,js,mjs,cjs}`` present
    2. ``jest.config.*`` present
    3. ``vitest`` listed in ``devDependencies``
    4. ``jest`` listed in ``devDependencies``
    5. default to ``vitest`` (modern, faster — EC-005)

    Args:
        project_root: Path to the project root.

    Returns:
        Either ``"vitest"`` or ``"jest"``.
    """
    project_root_path = Path(project_root)

    for vitest_config_name in _VITEST_CONFIG_NAMES:
        if (project_root_path / vitest_config_name).is_file():
            return "vitest"

    for jest_config_name in _JEST_CONFIG_NAMES:
        if (project_root_path / jest_config_name).is_file():
            return "jest"

    package_json = _read_package_json(project_root_path)
    dev_dependencies = package_json.get("devDependencies", {})  # type: ignore[assignment]
    if isinstance(dev_dependencies, dict):
        if "vitest" in dev_dependencies:
            return "vitest"
        if "jest" in dev_dependencies:
            return "jest"

    return "vitest"


def detect_package_manager(project_root: str) -> str:
    """Detect the package manager from lockfile presence.

    Args:
        project_root: Path to the project root.

    Returns:
        One of ``"bun"``, ``"pnpm"``, ``"yarn"``, ``"npm"``, or ``"npx"`` when
        no lockfile is found (FR-004 default).
    """
    project_root_path = Path(project_root)

    for lockfile_name, package_manager_name in _LOCKFILE_TO_PACKAGE_MANAGER:
        if (project_root_path / lockfile_name).is_file():
            return package_manager_name

    return "npx"


def has_dependency(
    project_root: str,
    name: str,
    *,
    dev_only: bool = False,
) -> bool:
    """Check whether ``name`` appears in the project's package.json.

    Args:
        project_root: Path to the project root.
        name: Exact dependency identifier to look for (e.g. ``fast-check``).
        dev_only: When ``True`` ignore the regular ``dependencies`` block.

    Returns:
        ``True`` when the dependency is declared in the relevant block(s).
    """
    project_root_path = Path(project_root)
    package_json = _read_package_json(project_root_path)

    dev_dependencies = package_json.get("devDependencies", {})  # type: ignore[assignment]
    if isinstance(dev_dependencies, dict) and name in dev_dependencies:
        return True

    if dev_only:
        return False

    dependencies = package_json.get("dependencies", {})  # type: ignore[assignment]
    return isinstance(dependencies, dict) and name in dependencies
