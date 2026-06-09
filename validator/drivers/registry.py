# LiveSpec traceability anchors
# @spec(FR-002)

"""Driver registry — discovers and matches drivers against the project root."""

# @spec FR-002: Registry scans shipped manifests first, then project overrides.
# @spec AC-003: Built-in manifests under livespec/drivers are auto-discovered.
# @spec AC-004: Custom manifests under .specs/drivers override built-ins by name.
# @spec AC-005: detect.files patterns are matched against the project root.
# @spec AC-006: Custom manifests sort before built-ins, then alphabetical by filename.

from __future__ import annotations

from pathlib import Path

from .loader import load_manifest
from .schemas import DriverManifest


def _builtin_drivers_dir() -> Path:
    """Return the directory holding shipped built-in driver YAMLs.

    Returns:
        Absolute path to the repository's ``livespec/drivers`` directory.
    """
    # Layout: <repo>/livespec/drivers/*.yaml (sibling of the validator package).
    return Path(__file__).resolve().parent.parent.parent / "livespec" / "drivers"


def _custom_drivers_dir(project_root: Path) -> Path:
    """Return the project-local custom driver directory.

    Args:
        project_root: Repository root being inspected.

    Returns:
        ``.specs/drivers`` under the supplied project root.
    """
    return project_root / ".specs" / "drivers"


def _scan(directory: Path, *, is_custom: bool) -> list[DriverManifest]:
    """Load every manifest file in a driver directory.

    Args:
        directory: Directory to scan for ``*.yaml`` manifest files.
        is_custom: Whether discovered manifests should be tagged as custom.

    Returns:
        Valid manifests from the directory, ordered alphabetically by filename.
    """
    if not directory.is_dir():
        return []
    out: list[DriverManifest] = []
    for path in sorted(directory.glob("*.yaml")):
        manifest = load_manifest(path, is_custom=is_custom)
        if manifest is not None:
            out.append(manifest)
    return out


def _matches(manifest: DriverManifest, project_root: Path) -> bool:
    """Return whether a manifest's detect rules match the project root.

    Args:
        manifest: Driver manifest under evaluation.
        project_root: Repository root being inspected.

    Returns:
        ``True`` when any configured top-level file glob matches.
    """
    patterns = manifest.detect.files
    if not patterns:
        return False
    # Top-level glob only — keep detection cheap (< 100ms).
    return any(any(project_root.glob(pat)) for pat in patterns)


class DriverRegistry:
    """Discover and rank drivers for one repository.

    Args:
        project_root: Repository root whose files are used for driver detection.
        builtin_dir: Optional override for the shipped built-in manifest directory.
    """

    def __init__(
        self,
        project_root: Path,
        *,
        builtin_dir: Path | None = None,
    ) -> None:
        self.project_root = project_root
        self.builtin_dir = builtin_dir or _builtin_drivers_dir()
        self._all_drivers: list[DriverManifest] = []
        self._matching: list[DriverManifest] = []

    def discover(self) -> list[DriverManifest]:
        """Scan built-in + custom dirs, return drivers matching project_root.

        Returns:
            Matching manifests ordered by priority: custom overrides first, then
            shipped built-ins, with alphabetical ordering preserved within each tier.
        """
        builtin = _scan(self.builtin_dir, is_custom=False)
        custom = _scan(_custom_drivers_dir(self.project_root), is_custom=True)
        # Custom > built-in. Drop a built-in if a custom shares the same name.
        custom_names = {m.name for m in custom}
        merged: list[DriverManifest] = list(custom) + [
            m for m in builtin if m.name not in custom_names
        ]
        self._all_drivers = merged
        self._matching = [m for m in merged if _matches(m, self.project_root)]
        return self._matching

    def all(self) -> list[DriverManifest]:
        """Return every loaded driver, whether or not it matches.

        Returns:
            All loaded manifests after triggering discovery on first access.
        """
        if not self._all_drivers:
            self.discover()
        return list(self._all_drivers)

    def matching(self) -> list[DriverManifest]:
        """Return the subset of loaded drivers that match the project root.

        Returns:
            Matching manifests after triggering discovery on first access.
        """
        if not self._all_drivers:
            self.discover()
        return list(self._matching)

    def primary(self) -> DriverManifest | None:
        """Return the highest-priority matching driver, if any."""
        matching_drivers = self.matching()
        return matching_drivers[0] if matching_drivers else None

    def find(self, name: str) -> DriverManifest | None:
        """Look up a driver by its manifest name.

        Args:
            name: Driver name to locate.

        Returns:
            The matching manifest, if it was loaded during discovery.
        """
        for driver in self.all():
            if driver.name == name:
                return driver
        return None
