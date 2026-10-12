# LiveSpec traceability anchors
# @spec(AC-008)
# @spec(AC-009)

"""Skip built-in TypeScript capabilities whose library is not installed."""

# @spec AC-008: Properties skips with a warning when fast-check is absent
# — .specs/features/018-driver-typescript-javascript/spec.md#ac-008
# @spec AC-009: Mutation emits an install hint when @stryker-mutator/core is absent
# — .specs/features/018-driver-typescript-javascript/spec.md#ac-009

from __future__ import annotations

from pathlib import Path

from .schemas import DriverManifest
from .typescript_detector import detect_package_manager, has_dependency, package_manager_add_dev

# capability -> (package, devDependencies only, label)
_TYPESCRIPT_REQUIREMENTS: dict[str, tuple[str, bool, str]] = {
    "properties": ("fast-check", False, "Properties"),
    "mutation": ("@stryker-mutator/core", True, "Mutation"),
}


def capability_skip_message(
    driver: DriverManifest, capability: str, project_root: Path
) -> str | None:
    """Return a skip message when a built-in capability's library is missing.

    Custom manifests under ``.specs/drivers`` own their commands and are never
    skipped here.

    Args:
        driver: Driver whose capability is about to run.
        capability: Capability name.
        project_root: Project whose ``package.json`` is inspected.

    Returns:
        A one-line skip/install hint, or None when the capability should run.
    """
    if driver.is_custom or driver.name != "typescript":
        return None
    requirement = _TYPESCRIPT_REQUIREMENTS.get(capability)
    if requirement is None:
        return None
    package, dev_only, label = requirement
    root = str(project_root)
    if has_dependency(root, package, dev_only=dev_only):
        return None
    install = package_manager_add_dev(detect_package_manager(root))
    return f"{label}: {package} not found in package.json — skipping. Install: {install} {package}"


__all__ = ["capability_skip_message"]
