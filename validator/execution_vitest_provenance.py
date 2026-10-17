"""Freeze and independently recheck Node, installed modules and owned hook identities."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

from .execution_scope import digest


def _tree_identity(root: Path) -> str:
    entries: dict[str, str] = {}
    confined = root.resolve(strict=True)
    # Include all installed transitive modules, including linked package contents.
    visited: set[Path] = set()
    for directory, dirs, files in os.walk(root, followlinks=True):
        base = Path(directory)
        real = base.resolve(strict=True)
        if not real.is_relative_to(confined):
            raise ValueError("Vitest dependency symlink escapes its installed module tree")
        if real in visited:
            dirs[:] = []
            continue
        visited.add(real)
        dirs[:] = sorted(name for name in dirs if name not in {".cache", ".vite", ".vite-temp"})
        for name in dirs:
            child = base / name
            if child.is_symlink():
                entries[str(child.relative_to(root)) + ":link"] = os.readlink(child)
        for name in sorted(files):
            path = base / name
            relative = str(path.relative_to(root))
            if path.is_symlink():
                if not path.resolve(strict=True).is_relative_to(confined):
                    raise ValueError("Vitest dependency file escapes its installed module tree")
                entries[relative + ":link"] = os.readlink(path)
            entries[relative] = digest(path.read_bytes())
    return digest(json.dumps(entries, sort_keys=True).encode())


# @spec FR-003: Bind native runtime, installed modules, package lock and owned assets
# — .specs/features/096-node-vitest-execution/spec.md#fr-003
def vitest_provenance(
    node: Path, package: Path, config: Path | None, project: Path | None = None
) -> dict[str, str]:
    """Bind every installed module, native interpreter, package lock and owned asset."""
    project = project or package
    modules = package / "node_modules"
    for name in ("vitest", "@vitest/runner", "@vitest/expect"):
        metadata = json.loads((modules / name / "package.json").read_bytes())
        if not isinstance(metadata, dict):
            raise ValueError(f"Invalid local {name} package metadata")
        if metadata.get("name") != name or not re.fullmatch(
            r"2\.1\.\d+", str(metadata.get("version", ""))
        ):
            raise ValueError(f"Unsupported local {name}; Vitest 2.1.x is required")
    locks = [
        path
        for path in (package / "package-lock.json", package.parent / "package-lock.json")
        if path.is_file() and path.resolve().is_relative_to(project)
    ]
    if not locks:
        raise ValueError("Vitest observation requires an existing npm package-lock.json")
    assets = Path(__file__).with_name("vitest")
    if not (assets / "config.ts").is_file():
        raise ValueError("Packaged Vitest observation assets are unavailable")
    return {
        "runner": "vitest",
        "project_root": str(project),
        "node_path": str(node),
        "node_sha256": digest(node.read_bytes()),
        "package_root": str(package),
        "package_sha256": digest((package / "package.json").read_bytes()),
        "lock_path": str(locks[0]),
        "lock_sha256": digest(locks[0].read_bytes()),
        "config_path": str(config) if config else "",
        "config_sha256": digest(config.read_bytes()) if config else "",
        "modules_sha256": _tree_identity(modules),
        "assets_sha256": _tree_identity(assets),
    }


def current_vitest_provenance(recorded: dict[str, str]) -> dict[str, str]:
    """Recompute exactly the same external identities at consumption boundaries."""
    required = {"node_path", "package_root", "project_root", "config_path"}
    if not required.issubset(recorded) or any(
        not recorded[name] for name in required - {"config_path"}
    ):
        raise ValueError("Incomplete recorded Vitest runtime provenance")
    config = recorded.get("config_path")
    return vitest_provenance(
        Path(recorded["node_path"]),
        Path(recorded["package_root"]),
        Path(config) if config else None,
        Path(recorded["project_root"]),
    )
