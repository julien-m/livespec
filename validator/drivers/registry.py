"""Driver registry — discovers and matches drivers against the project root."""

# @spec FR-002: DriverRegistry with built-in + custom scan — .specs/features/016-cross-language-test-driver-architecture/spec.md#fr-002  # noqa: E501
# @spec AC-003: Built-in drivers under livespec/drivers/ auto-discovered — .specs/features/016-cross-language-test-driver-architecture/spec.md#ac-003  # noqa: E501
# @spec AC-004: Custom drivers under .specs/drivers/ override built-in — .specs/features/016-cross-language-test-driver-architecture/spec.md#ac-004  # noqa: E501
# @spec AC-005: detect.files glob matching — .specs/features/016-cross-language-test-driver-architecture/spec.md#ac-005  # noqa: E501
# @spec AC-006: Custom > built-in; alphabetical tie-break — .specs/features/016-cross-language-test-driver-architecture/spec.md#ac-006  # noqa: E501


from __future__ import annotations

from pathlib import Path

from .loader import load_manifest
from .schemas import DriverManifest


def _builtin_drivers_dir() -> Path:
    """Return the directory holding shipped built-in driver YAMLs."""
    # Layout: <repo>/livespec/drivers/*.yaml (sibling of the validator package).
    return Path(__file__).resolve().parent.parent.parent / "livespec" / "drivers"


def _custom_drivers_dir(project_root: Path) -> Path:
    return project_root / ".specs" / "drivers"


def _scan(directory: Path, *, is_custom: bool) -> list[DriverManifest]:
    if not directory.is_dir():
        return []
    out: list[DriverManifest] = []
    for path in sorted(directory.glob("*.yaml")):
        manifest = load_manifest(path, is_custom=is_custom)
        if manifest is not None:
            out.append(manifest)
    return out


def _matches(manifest: DriverManifest, project_root: Path) -> bool:
    patterns = manifest.detect.files
    if not patterns:
        return False
    # Top-level glob only — keep detection cheap (< 100ms).
    return any(any(project_root.glob(pat)) for pat in patterns)


class DriverRegistry:
    """Ordered list of drivers matching the current project."""

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

        Custom drivers come first; alphabetical order within each tier is preserved
        from `_scan`'s `sorted(...)`.
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
        """Return every loaded driver (matching or not). Triggers discover() if needed."""
        if not self._all_drivers:
            self.discover()
        return list(self._all_drivers)

    def matching(self) -> list[DriverManifest]:
        if not self._all_drivers:
            self.discover()
        return list(self._matching)

    def primary(self) -> DriverManifest | None:
        m = self.matching()
        return m[0] if m else None

    def find(self, name: str) -> DriverManifest | None:
        for d in self.all():
            if d.name == name:
                return d
        return None
