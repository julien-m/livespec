"""Isolated genuine Node/Vitest projects; dependencies are never installed by capture."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest

from validator.execution_capture import capture_execution
from validator.execution_scope import digest

FEATURE = "001-matchers"
IMPORTS = "import { test, expect, afterEach, vi, chai } from 'vitest';\n"


@dataclass(frozen=True)
class VitestProject:
    """Own one isolated project and the actual native Node executable."""

    root: Path
    node: Path

    def command(self, *selection: str) -> list[str]:
        """Build the supported direct argv, without shell or npm wrappers."""
        return [
            str(self.node),
            str(self.root / "node_modules/vitest/vitest.mjs"),
            "run",
            *selection,
        ]

    def write(self, source: str, name: str = "matchers.test.ts") -> Path:
        """Write this case's genuine test source inside its isolated project."""
        path = self.root / name
        path.write_text(IMPORTS + source)
        return path

    def capture(self, *selection: str, timeout: float = 10) -> Path:
        """Run the public capture boundary with a bounded real subprocess."""
        result = capture_execution(
            self.command(*selection),
            project_root=self.root,
            feature=FEATURE,
            adapter="junit",
            env=dict(os.environ),
            timeout=timeout,
        )
        assert result.receipt_path, result.stderr
        return Path(result.receipt_path)

    def replace_artifact(self, receipt: Path, name: str, payload: bytes) -> None:
        """Intentionally corrupt a read-only artifact to test evidence refusal."""
        path = receipt.parent / name
        path.chmod(0o600)
        path.write_bytes(payload)

    def replace_inventory(self, receipt: Path, payload: bytes) -> None:
        """Rebind corrupt inventory hashes to exercise semantic checks beyond tamper detection."""
        self.replace_artifact(receipt, "inventory", payload)
        capture_path = receipt.parent / "capture.json"
        capture = json.loads(capture_path.read_text())
        capture["vitest_inventory_sha256"] = digest(payload)
        self.replace_artifact(receipt, "capture.json", json.dumps(capture).encode())
        reference = json.loads(receipt.read_text())
        reference["capture_sha256"] = digest(capture_path.read_bytes())
        self.replace_artifact(receipt, receipt.name, json.dumps(reference).encode())


def _runtime() -> Path:
    configured = os.environ.get("LIVESPEC_VITEST_NODE") or shutil.which("node")
    if not configured:
        pytest.skip("Node 22 unavailable; set LIVESPEC_VITEST_NODE to its native executable")
    node = Path(configured).resolve(strict=True)
    # Verify the binary before preparing files; this is fixture preparation, never capture fallback.
    version = subprocess.run([str(node), "--version"], capture_output=True, text=True, timeout=3)
    if version.returncode or not version.stdout.startswith("v22."):
        pytest.skip(
            "Node 22 required; set LIVESPEC_VITEST_NODE (found " + version.stdout.strip() + ")"
        )
    return node


def _copy_dependencies(source: Path, destination: Path) -> None:
    """Copy Vitest's installed production closure, including native optional packages."""
    pending = ["vitest"]
    copied: set[str] = set()
    while pending:
        name = pending.pop()
        if name in copied:
            continue
        package = source / name
        if not (package / "package.json").is_file():
            continue  # Optional platform dependencies are absent on other operating systems.
        metadata = json.loads((package / "package.json").read_text())
        copied.add(name)
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(package, target)
        pending.extend(metadata.get("dependencies", {}))
        pending.extend(metadata.get("optionalDependencies", {}))


@pytest.fixture(scope="session")
def vitest_dependencies(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Path]:
    """Copy the supplied installation once; no user-specific path or network fallback."""
    node = _runtime()
    source = Path(os.environ.get("LIVESPEC_VITEST_NODE_MODULES", "node_modules")).resolve()
    manifest = source / "vitest/package.json"
    if not manifest.is_file():
        pytest.skip("Local Vitest unavailable; set LIVESPEC_VITEST_NODE_MODULES to node_modules")
    if json.loads(manifest.read_text()).get("version") != "2.1.9":
        pytest.skip("Real fixture requires Vitest 2.1.9")
    modules = tmp_path_factory.mktemp("vitest-dependencies") / "node_modules"
    _copy_dependencies(source, modules)
    return node, modules


@pytest.fixture
def vitest_project(tmp_path: Path, vitest_dependencies: tuple[Path, Path]) -> VitestProject:
    """Give each case independent files and modules, so mutation cannot leak between cases."""
    node, modules = vitest_dependencies
    root = tmp_path / "project"
    root.mkdir()
    shutil.copytree(modules, root / "node_modules")
    (root / "package.json").write_text(
        json.dumps({"name": "matcher-fixture", "private": True, "type": "module"})
    )
    (root / "vitest.config.ts").write_text(
        "export default { test: { maxWorkers: 1, minWorkers: 1 } };\n"
    )
    (root / "package-lock.json").write_text(
        json.dumps({"name": "matcher-fixture", "lockfileVersion": 3, "packages": {}})
    )
    feature = root / ".specs/features" / FEATURE
    feature.mkdir(parents=True)
    (feature / "spec.md").write_text("# Matcher fixture\nAC-001: A real matcher runs.\n")
    return VitestProject(root, node)
