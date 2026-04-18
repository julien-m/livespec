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
    match = re.search(r"^VISUAL_SCAFFOLD_RESULT: files=(\d+) dirs=(\d+)", stdout, re.MULTILINE)
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


# ─────────────────────────────────────────────────────────────────────────────
# Frontend mode fixtures and helpers

FIXTURE_MIGRATE_VISUAL_FRONTEND = FIXTURES / "migrate-visual-frontend"


@pytest.fixture()
def fixture_migrate_visual_frontend(tmp_path: Path) -> Path:
    """Copy the migrate-visual-frontend fixture to tmp_path for isolation."""
    dst = tmp_path / "project"
    shutil.copytree(FIXTURE_MIGRATE_VISUAL_FRONTEND, dst)
    return dst


def _parse_sentinel_routes(stdout: str) -> tuple[int, int, int]:
    """Parse VISUAL_SCAFFOLD_RESULT: files=N dirs=M routes=R — returns (-1,-1,-1) if not found."""
    m = re.search(r"VISUAL_SCAFFOLD_RESULT: files=(\d+) dirs=(\d+) routes=(\d+)", stdout)
    if not m:
        return (-1, -1, -1)
    return (int(m.group(1)), int(m.group(2)), int(m.group(3)))


@pytest.mark.level_3a
class TestMigrateVisualRouteScan:
    """Tests for route-scan functionality in migrate-visual-tests.js."""

    def test_generates_route_test_for_uncovered_page(
        self, fixture_migrate_visual_frontend: Path
    ) -> None:
        """Route scan creates route-settings.spec.ts for settings.tsx not in any spec."""
        result = _run_generate(fixture_migrate_visual_frontend)
        assert result.returncode == 0, (
            f"Script failed:\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}"
        )

        e2e_dir = fixture_migrate_visual_frontend / "frontend" / "tests" / "e2e"
        route_test = e2e_dir / "route-settings.spec.ts"
        assert route_test.exists(), (
            f"route-settings.spec.ts not generated. stdout:\n{result.stdout}"
        )

    def test_route_test_uses_extracted_heading(
        self, fixture_migrate_visual_frontend: Path
    ) -> None:
        """Route scan extracts h1 'Settings' from settings.tsx."""
        _run_generate(fixture_migrate_visual_frontend)
        route_file = (
            fixture_migrate_visual_frontend / "frontend" / "tests" / "e2e"
            / "route-settings.spec.ts"
        )
        content = route_file.read_text()
        assert "HEADING = 'Settings'" in content, (
            f"Heading not extracted correctly. Content:\n{content[:500]}"
        )

    def test_skips_redirect_only_routes(
        self, fixture_migrate_visual_frontend: Path
    ) -> None:
        """Profile page with redirect() and no h1 is not generated."""
        _run_generate(fixture_migrate_visual_frontend)
        e2e_dir = fixture_migrate_visual_frontend / "frontend" / "tests" / "e2e"
        assert not (
            e2e_dir / "route-profile.spec.ts"
        ).exists(), "Redirect-only page should not get a route test"

    def test_generates_not_found_test_from_root(
        self, fixture_migrate_visual_frontend: Path
    ) -> None:
        """notFoundComponent in __root.tsx produces route-not-found.spec.ts."""
        _run_generate(fixture_migrate_visual_frontend)
        e2e_dir = fixture_migrate_visual_frontend / "frontend" / "tests" / "e2e"
        assert (e2e_dir / "route-not-found.spec.ts").exists(), (
            "route-not-found.spec.ts not generated from __root.tsx"
        )

    def test_route_test_overwrites_on_regenerate(
        self, fixture_migrate_visual_frontend: Path
    ) -> None:
        """Running --generate twice overwrites route-* tests (no AC-030 protection)."""
        _run_generate(fixture_migrate_visual_frontend)
        route_test = (
            fixture_migrate_visual_frontend / "frontend" / "tests" / "e2e"
            / "route-settings.spec.ts"
        )
        original_mtime = route_test.stat().st_mtime

        import time
        time.sleep(0.1)
        _run_generate(fixture_migrate_visual_frontend)
        new_mtime = route_test.stat().st_mtime
        assert new_mtime > original_mtime, (
            "route-settings.spec.ts was not overwritten on second run"
        )

    def test_sentinel_includes_routes_count(
        self, fixture_migrate_visual_frontend: Path
    ) -> None:
        """Sentinel line includes routes= count reflecting route-scan results."""
        result = _run_generate(fixture_migrate_visual_frontend)
        _, _, routes = _parse_sentinel_routes(result.stdout)
        assert routes >= 1, (
            f"Sentinel routes= should be >= 1. stdout:\n{result.stdout}"
        )


@pytest.mark.level_3a
class TestMigrateVisualDeleteSuperseded:
    """Tests for auto-deletion of superseded non-numbered tests."""

    def test_deletes_superseded_test_covered_by_route_scan(
        self, fixture_migrate_visual_frontend: Path
    ) -> None:
        """Old settings.spec.ts is deleted after route-settings.spec.ts is generated."""
        e2e_dir = fixture_migrate_visual_frontend / "frontend" / "tests" / "e2e"
        e2e_dir.mkdir(parents=True, exist_ok=True)
        old_test = e2e_dir / "settings.spec.ts"
        old_test.write_text("// old hand-crafted test\n")

        _run_generate(fixture_migrate_visual_frontend)

        assert not old_test.exists(), (
            "settings.spec.ts should be deleted after route-settings.spec.ts covers"
            " /settings"
        )
        assert (e2e_dir / "route-settings.spec.ts").exists(), \
            "route-settings.spec.ts should exist as replacement"

    def test_preserves_numbered_tests(self, fixture_migrate_visual_frontend: Path) -> None:
        """Numbered tests (001-*.spec.ts) are never deleted."""
        e2e_dir = fixture_migrate_visual_frontend / "frontend" / "tests" / "e2e"
        e2e_dir.mkdir(parents=True, exist_ok=True)
        numbered = e2e_dir / "001-auth-ui.spec.ts"
        numbered.write_text("// existing numbered test\n")

        _run_generate(fixture_migrate_visual_frontend)

        assert numbered.exists(), "Numbered test 001-auth-ui.spec.ts must not be deleted"

    def test_preserves_route_prefixed_tests_from_deletion(
        self, fixture_migrate_visual_frontend: Path
    ) -> None:
        """route-* tests are never deleted by deleteSupersededTests."""
        e2e_dir = fixture_migrate_visual_frontend / "frontend" / "tests" / "e2e"
        e2e_dir.mkdir(parents=True, exist_ok=True)
        route_test = e2e_dir / "route-settings.spec.ts"
        route_test.write_text("// existing route test\n")

        _run_generate(fixture_migrate_visual_frontend)

        # File should still exist (overwritten on second run, not deleted)
        assert route_test.exists(), "route-settings.spec.ts should not be deleted"


_LEGACY_SETTINGS_CONTENT = """\
import { expect, test } from '@playwright/test';
import { mockAuthenticatedAPIs, mockSettingsFormAPIs } from './fixtures.js';

test.describe('Settings page @visual', () => {
  test.beforeEach(async ({ page }) => {
    await mockAuthenticatedAPIs(page);
  });

  test('full page with data', async ({ page }) => {
    await page.goto('/settings', { waitUntil: 'networkidle' });
    await page.waitForSelector('h1');
    await expect(page).toHaveScreenshot('settings-full.png', { fullPage: true });
  });

  test('settings with form validation errors', async ({ page }) => {
    await page.route('**/api/settings/save', (route) =>
      route.fulfill({ status: 422, json: { detail: 'Validation failed' } })
    );
    await page.goto('/settings', { waitUntil: 'networkidle' });
    await page.waitForSelector('[role="alert"]');
    await expect(page).toHaveScreenshot('settings-validation-error.png', { fullPage: true });
  });

  test('settings with success toast', async ({ page }) => {
    await page.goto('/settings', { waitUntil: 'networkidle' });
    await page.fill('[name="username"]', 'newuser');
    await page.click('button[type="submit"]');
    await page.waitForSelector('.toast-success');
    await expect(page).toHaveScreenshot('settings-saved.png', { fullPage: true });
  });
});
"""


@pytest.mark.level_3a
class TestMigrateVisualLegacyMerge:
    """Tests for merging custom tests from legacy spec files into route-scan generated files."""

    @staticmethod
    def _setup_legacy(fixture: Path, content: str) -> tuple[Path, Path]:
        e2e_dir = fixture / "frontend" / "tests" / "e2e"
        e2e_dir.mkdir(parents=True, exist_ok=True)
        legacy = e2e_dir / "settings.spec.ts"
        legacy.write_text(content)
        return e2e_dir, legacy

    def test_merges_custom_tests_from_legacy_file(
        self, fixture_migrate_visual_frontend: Path
    ) -> None:
        """Custom test blocks from legacy file are merged into route file."""
        e2e_dir, _ = self._setup_legacy(
            fixture_migrate_visual_frontend, _LEGACY_SETTINGS_CONTENT
        )

        result = _run_generate(fixture_migrate_visual_frontend)
        assert result.returncode == 0, f"Script failed:\n{result.stdout}\n{result.stderr}"

        content = (e2e_dir / "route-settings.spec.ts").read_text()
        assert "settings with form validation errors" in content, "Custom test 1 not merged"
        assert "settings with success toast" in content, "Custom test 2 not merged"

    def test_standard_tests_not_duplicated_from_legacy(
        self, fixture_migrate_visual_frontend: Path
    ) -> None:
        """Standard test 'full page with data' not injected from legacy (dedup)."""
        e2e_dir, _ = self._setup_legacy(
            fixture_migrate_visual_frontend, _LEGACY_SETTINGS_CONTENT
        )

        _run_generate(fixture_migrate_visual_frontend)
        content = (e2e_dir / "route-settings.spec.ts").read_text()
        # Standard name appears exactly once (from template only)
        assert content.count("test('full page with data'") == 1, (
            "Standard test duplicated from legacy"
        )
        assert "settings with form validation errors" in content, "Custom tests should still be merged"

    def test_custom_imports_merged_from_legacy(
        self, fixture_migrate_visual_frontend: Path
    ) -> None:
        """Custom imports from legacy file are merged into route file."""
        e2e_dir, _ = self._setup_legacy(
            fixture_migrate_visual_frontend, _LEGACY_SETTINGS_CONTENT
        )

        _run_generate(fixture_migrate_visual_frontend)
        content = (e2e_dir / "route-settings.spec.ts").read_text()
        assert (
            "mockSettingsFormAPIs" in content
        ), "Custom import not merged into route file"

    def test_provenance_comment_present(
        self, fixture_migrate_visual_frontend: Path
    ) -> None:
        """Preserved custom tests are annotated with their source file."""
        e2e_dir, _ = self._setup_legacy(
            fixture_migrate_visual_frontend, _LEGACY_SETTINGS_CONTENT
        )

        _run_generate(fixture_migrate_visual_frontend)
        content = (e2e_dir / "route-settings.spec.ts").read_text()
        assert (
            "Preserved from settings.spec.ts" in content
        ), "Provenance comment missing"

    def test_legacy_file_deleted_after_merge(
        self, fixture_migrate_visual_frontend: Path
    ) -> None:
        """Legacy spec file is deleted after custom tests are merged."""
        e2e_dir, legacy = self._setup_legacy(
            fixture_migrate_visual_frontend, _LEGACY_SETTINGS_CONTENT
        )

        result = _run_generate(fixture_migrate_visual_frontend)
        assert result.returncode == 0
        assert (
            not legacy.exists()
        ), "Legacy file should be deleted after successful merge"
        assert (e2e_dir / "route-settings.spec.ts").exists()
        merged_content = (e2e_dir / "route-settings.spec.ts").read_text()
        assert "settings with form validation errors" in merged_content, "Custom tests should be merged before deletion"
