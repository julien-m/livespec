"""Unit tests for TypeScript/JavaScript runner and package manager detection."""

# @spec FR-006: Unit tests for runner detection and parser
# — .specs/features/018-driver-typescript-javascript/spec.md#fr-006

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from validator.drivers.typescript_detector import (
    detect_package_manager,
    detect_test_runner,
    has_dependency,
)


def _write_package_json(project_root: Path, payload: dict[str, object]) -> None:
    """Helper that writes a package.json into ``project_root``."""
    (project_root / "package.json").write_text(
        json.dumps(payload),
        encoding="utf-8",
    )


def test_detect_test_runner_prefers_vitest_config() -> None:
    """A vitest config beats every other signal."""
    # @spec AC-002 — .specs/features/018-driver-typescript-javascript/spec.md#ac-002
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        (project_root / "vitest.config.ts").write_text("export default {}", encoding="utf-8")
        (project_root / "jest.config.js").write_text("module.exports = {}", encoding="utf-8")

        assert detect_test_runner(str(project_root)) == "vitest"


def test_detect_test_runner_uses_jest_config_when_no_vitest() -> None:
    """Jest config wins when vitest config is absent."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        (project_root / "jest.config.js").write_text("module.exports = {}", encoding="utf-8")

        assert detect_test_runner(str(project_root)) == "jest"


def test_detect_test_runner_devdependencies_vitest() -> None:
    """devDependencies fall back to vitest when no config file is present."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        _write_package_json(project_root, {"devDependencies": {"vitest": "^1.0.0"}})

        assert detect_test_runner(str(project_root)) == "vitest"


def test_detect_test_runner_devdependencies_jest() -> None:
    """devDependencies fall back to jest when only jest is declared."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        _write_package_json(project_root, {"devDependencies": {"jest": "^29.0.0"}})

        assert detect_test_runner(str(project_root)) == "jest"


def test_detect_test_runner_default_vitest_when_nothing() -> None:
    """No config and no devDependencies signal yields the modern default."""
    # @spec EC-005 — vitest takes priority when both runners coexist or neither
    # is configured.
    with tempfile.TemporaryDirectory() as tmpdir:
        assert detect_test_runner(tmpdir) == "vitest"


def test_detect_package_manager_bun_lockfile() -> None:
    """``bun.lockb`` selects the ``bun`` package manager."""
    # @spec FR-004 — .specs/features/018-driver-typescript-javascript/spec.md#fr-004
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        (project_root / "bun.lockb").write_text("", encoding="utf-8")

        assert detect_package_manager(str(project_root)) == "bun"


def test_detect_package_manager_pnpm_lockfile() -> None:
    """``pnpm-lock.yaml`` selects the ``pnpm`` package manager."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        (project_root / "pnpm-lock.yaml").write_text("", encoding="utf-8")

        assert detect_package_manager(str(project_root)) == "pnpm"


def test_detect_package_manager_yarn_lockfile() -> None:
    """``yarn.lock`` selects the ``yarn`` package manager."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        (project_root / "yarn.lock").write_text("", encoding="utf-8")

        assert detect_package_manager(str(project_root)) == "yarn"


def test_detect_package_manager_npm_lockfile() -> None:
    """``package-lock.json`` selects the ``npm`` package manager."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        (project_root / "package-lock.json").write_text("{}", encoding="utf-8")

        assert detect_package_manager(str(project_root)) == "npm"


def test_detect_package_manager_default_npx() -> None:
    """No lockfile present yields the ``npx`` default."""
    with tempfile.TemporaryDirectory() as tmpdir:
        assert detect_package_manager(tmpdir) == "npx"


def test_detect_package_manager_bun_wins_over_pnpm() -> None:
    """When several lockfiles coexist, the most specific one wins."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        (project_root / "bun.lockb").write_text("", encoding="utf-8")
        (project_root / "pnpm-lock.yaml").write_text("", encoding="utf-8")

        assert detect_package_manager(str(project_root)) == "bun"


def test_has_dependency_finds_in_dependencies() -> None:
    """A dependency declared in ``dependencies`` is detected."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        _write_package_json(project_root, {"dependencies": {"fast-check": "^3.0.0"}})

        assert has_dependency(str(project_root), "fast-check") is True


def test_has_dependency_finds_in_dev_dependencies() -> None:
    """A dependency declared in ``devDependencies`` is detected."""
    # @spec AC-009 — Stryker is typically a dev dependency.
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        _write_package_json(
            project_root,
            {"devDependencies": {"@stryker-mutator/core": "^8.0.0"}},
        )

        assert (
            has_dependency(str(project_root), "@stryker-mutator/core", dev_only=True)
            is True
        )


def test_has_dependency_returns_false_when_absent() -> None:
    """Missing dependency yields ``False``."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        _write_package_json(project_root, {"dependencies": {"react": "^18.0.0"}})

        assert has_dependency(str(project_root), "fast-check") is False


def test_has_dependency_handles_missing_package_json() -> None:
    """Missing ``package.json`` should not raise."""
    with tempfile.TemporaryDirectory() as tmpdir:
        assert has_dependency(tmpdir, "fast-check") is False


def test_has_dependency_handles_malformed_package_json() -> None:
    """Malformed ``package.json`` should degrade to ``False`` instead of crashing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        (project_root / "package.json").write_text("not valid json {{{", encoding="utf-8")

        assert has_dependency(str(project_root), "fast-check") is False
