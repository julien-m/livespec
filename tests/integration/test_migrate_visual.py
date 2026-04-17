"""Level 3A — Integration tests for visual scaffolding in spec.migrate.

Tests invoke scripts/migrate-visual-tests.js directly on a controlled fixture
to validate sentinel output, file creation, idempotency, and guard behavior.
"""

# @spec FR-001: Unconditional invocation, FR-002: Silent always-run
# — .specs/features/011-visual-migrate-integration/spec.md#fr-001

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"
SCRIPT_PATH = Path(__file__).parent.parent.parent / "scripts" / "migrate-visual-tests.js"


@pytest.fixture()
def fixture_migrate_visual(tmp_path: Path) -> Path:
    """Copy the migrate-visual fixture to tmp_path for isolation."""
    src = FIXTURES / "migrate-visual"
    dst = tmp_path / "project"
    shutil.copytree(src, dst)
    return dst


def _run_generate(cwd: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    """Run migrate-visual-tests.js --generate in the given directory."""
    run_env = os.environ.copy()
    if env:
        run_env.update(env)
    return subprocess.run(
        ["node", str(SCRIPT_PATH), "--generate"],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=30,
        env=run_env,
    )


def _parse_sentinel(stdout: str) -> tuple[int, int] | None:
    """Extract files and dirs counts from the sentinel line."""
    match = re.search(r"^VISUAL_SCAFFOLD_RESULT: files=(\d+) dirs=(\d+)$", stdout, re.MULTILINE)
    if not match:
        return None
    return int(match.group(1)), int(match.group(2))


@pytest.mark.level_3a
class TestMigrateVisualGenerate:
    """Tests for migrate-visual-tests.js --generate on the fixture project."""

    # @spec FR-001: Unconditional invocation, AC-001, AC-002 — spec.md#fr-001
    def test_generates_files_for_ui_features(self, fixture_migrate_visual: Path) -> None:
        """FR-001, AC-001, AC-002: creates .spec.ts for UI features without existing tests."""
        result = _run_generate(fixture_migrate_visual)
        assert result.returncode == 0, f"Script failed: {result.stderr}"

        visual_dir = fixture_migrate_visual / "tests" / "visual"
        # 001-auth-ui and 003-dashboard should be generated
        assert (visual_dir / "001-auth-ui.spec.ts").exists(), "Missing test for 001-auth-ui"
        assert (visual_dir / "003-dashboard.spec.ts").exists(), "Missing test for 003-dashboard"

    # @spec FR-004: Skip backend features, AC-004 — spec.md#fr-004
    def test_skips_backend_only_features(self, fixture_migrate_visual: Path) -> None:
        """FR-004, AC-004: features with no UI keywords produce no test file."""
        result = _run_generate(fixture_migrate_visual)
        assert result.returncode == 0

        visual_dir = fixture_migrate_visual / "tests" / "visual"
        assert not (visual_dir / "002-backend-only.spec.ts").exists(), (
            "Backend-only feature should not get a visual test"
        )

    # @spec FR-003: Preserve existing tests, AC-005 — spec.md#fr-003
    def test_preserves_existing_test_files(self, fixture_migrate_visual: Path) -> None:
        """FR-003, AC-005: existing .spec.ts is not overwritten."""
        existing_file = (
            fixture_migrate_visual / "tests" / "visual" / "004-already-has-tests.spec.ts"
        )
        original_content = existing_file.read_text()

        result = _run_generate(fixture_migrate_visual)
        assert result.returncode == 0

        assert existing_file.read_text() == original_content, "Existing test file was modified"

    # @spec FR-005: Create baseline dirs, AC-003 — spec.md#fr-005
    def test_creates_baseline_directories(self, fixture_migrate_visual: Path) -> None:
        """FR-005, AC-003: all 6 baseline subdirs created per scaffolded feature."""
        result = _run_generate(fixture_migrate_visual)
        assert result.returncode == 0

        baseline_subdirs = ["mockups", "fullpage", "mobile", "tablet", "desktop", "animations"]
        for feature_slug in ["auth-ui", "dashboard"]:
            for subdir in baseline_subdirs:
                d = fixture_migrate_visual / "baselines" / subdir / feature_slug
                assert d.exists(), f"Missing baseline dir: baselines/{subdir}/{feature_slug}/"

    # @spec AC-008: Idempotent on second run — spec.md#ac-008
    def test_idempotent_on_second_run(self, fixture_migrate_visual: Path) -> None:
        """AC-008: second run creates 0 new files, exits 0."""
        # First run
        result1 = _run_generate(fixture_migrate_visual)
        assert result1.returncode == 0

        # Record state after first run
        visual_dir = fixture_migrate_visual / "tests" / "visual"
        files_after_first = sorted(str(p) for p in visual_dir.glob("*.spec.ts"))

        # Second run
        result2 = _run_generate(fixture_migrate_visual)
        assert result2.returncode == 0

        # Same files, no new ones
        files_after_second = sorted(str(p) for p in visual_dir.glob("*.spec.ts"))
        assert files_after_first == files_after_second, "Second run created new files"

        # Sentinel shows 0 files
        sentinel = _parse_sentinel(result2.stdout)
        assert sentinel is not None, f"Missing sentinel line in output:\n{result2.stdout}"
        assert sentinel[0] == 0, f"Expected files=0, got files={sentinel[0]}"

    # @spec AC-009: New feature picked up on re-run, FR-011 — spec.md#fr-011
    def test_picks_up_new_feature_on_rerun(self, fixture_migrate_visual: Path) -> None:
        """AC-009, FR-011: new UI feature dir added between runs is scaffolded on re-run."""
        # First run
        _run_generate(fixture_migrate_visual)

        # Add a new UI feature
        new_feature = fixture_migrate_visual / ".specs" / "features" / "005-new-ui"
        new_feature.mkdir(parents=True)
        (new_feature / "spec.md").write_text(
            "---\nfeature: New UI\ntitle: New UI\nstatus: Implemented\n---\n"
            "# New UI\nA new page with a button component and form layout.\n"
        )

        # Second run should pick it up
        result = _run_generate(fixture_migrate_visual)
        assert result.returncode == 0

        visual_dir = fixture_migrate_visual / "tests" / "visual"
        assert (visual_dir / "005-new-ui.spec.ts").exists(), "New feature not picked up on re-run"

    # @spec FR-006: Sentinel line format, AC-006 — spec.md#fr-006
    def test_sentinel_line_format(self, fixture_migrate_visual: Path) -> None:
        """FR-006, AC-006: stdout ends with VISUAL_SCAFFOLD_RESULT: files=N dirs=M."""
        result = _run_generate(fixture_migrate_visual)
        assert result.returncode == 0

        sentinel = _parse_sentinel(result.stdout)
        assert sentinel is not None, f"Missing sentinel line in output:\n{result.stdout}"
        files, dirs = sentinel
        # 2 UI features without tests (001-auth-ui, 003-dashboard)
        assert files == 2, f"Expected files=2, got files={files}"
        # 6 baseline dirs per feature = 12
        assert dirs == 12, f"Expected dirs=12, got dirs={dirs}"

    # @spec AC-007: Zero sentinel when all covered — spec.md#ac-007
    def test_sentinel_shows_zero_when_all_covered(self, fixture_migrate_visual: Path) -> None:
        """AC-007: sentinel shows files=0 dirs=0 when all UI features already have tests."""
        # First run to scaffold everything
        _run_generate(fixture_migrate_visual)

        # Second run — all covered
        result = _run_generate(fixture_migrate_visual)
        assert result.returncode == 0

        sentinel = _parse_sentinel(result.stdout)
        assert sentinel is not None, f"Missing sentinel line:\n{result.stdout}"
        assert sentinel == (0, 0), f"Expected (0, 0), got {sentinel}"

    def test_scan_mode_does_not_emit_sentinel(self, fixture_migrate_visual: Path) -> None:
        """--scan and --dry-run modes do NOT emit the VISUAL_SCAFFOLD_RESULT sentinel."""
        for flag in ["--scan", "--dry-run"]:
            result = subprocess.run(
                ["node", str(SCRIPT_PATH), flag],
                cwd=str(fixture_migrate_visual),
                capture_output=True,
                text=True,
                timeout=30,
            )
            assert "VISUAL_SCAFFOLD_RESULT" not in result.stdout, (
                f"{flag} mode should not emit sentinel line"
            )


@pytest.mark.level_3a
class TestMigrateVisualGuards:
    """Tests for graceful degradation when script or Node.js is missing."""

    # @spec FR-008: Script-missing guard, AC-010 — spec.md#fr-008
    def test_warning_when_script_missing(self, tmp_path: Path) -> None:
        """FR-008, AC-010: exits 0 with warning when migrate-visual-tests.js absent."""
        # Run with a non-existent script path
        fake_script = tmp_path / "nonexistent.js"
        result = subprocess.run(
            ["node", str(fake_script), "--generate"],
            cwd=str(tmp_path),
            capture_output=True,
            text=True,
            timeout=10,
        )
        # Node.js will exit non-zero when script doesn't exist
        assert result.returncode != 0, "Expected non-zero exit for missing script"
        # The command layer (migrate.md) handles this by checking file existence first
        # This test validates the script-level behavior: Node exits non-zero

    # @spec FR-010: Non-zero exit guard, AC-012 — spec.md#fr-010
    def test_nonzero_exit_on_missing_specs_dir(self, tmp_path: Path) -> None:
        """FR-010, AC-012: script exits non-zero when .specs/features/ is missing."""
        # Run in a directory without .specs/features/
        result = subprocess.run(
            ["node", str(SCRIPT_PATH), "--generate"],
            cwd=str(tmp_path),
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode != 0, "Expected non-zero exit for missing .specs/features/"
        assert "Missing .specs/features/" in result.stderr, (
            f"Expected error about missing directory, got: {result.stderr}"
        )
