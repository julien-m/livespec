"""Unit tests for the smart test selector.

See .specs/features/033-smart-test-selection/spec.md#fr-009 for details.
"""

import subprocess
import tempfile
from pathlib import Path

import pytest

from validator.selector import SmartTestSelector


@pytest.fixture
def temp_specs_dir() -> Path:
    """Create a temporary `.specs` directory structure for selector tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        specs_dir = root / ".specs"
        features_dir = specs_dir / "features"
        features_dir.mkdir(parents=True)

        feature_005 = features_dir / "005-notifications"
        feature_005.mkdir()
        (feature_005 / "spec.md").write_text("# Spec: Notifications\n", encoding="utf-8")
        (feature_005 / "implementation.md").write_text(
            "| Test | File |\n|---|---|\n| Unit | `tests/test_notifications.py` |\n",
            encoding="utf-8",
        )

        feature_008 = features_dir / "008-auth"
        feature_008.mkdir()
        (feature_008 / "spec.md").write_text("# Spec: Auth\n", encoding="utf-8")
        (feature_008 / "implementation.md").write_text(
            "| Test | File |\n|---|---|\n| Unit | `tests/test_auth.py` |\n",
            encoding="utf-8",
        )

        yield specs_dir


@pytest.fixture
def selector(temp_specs_dir: Path) -> SmartTestSelector:
    """Create a selector bound to the temporary project."""
    return SmartTestSelector(temp_specs_dir)


class TestAnchorParser:
    """Test anchor parsing logic."""

    def test_single_anchor_parsed(self, selector: SmartTestSelector) -> None:
        """A valid single anchor is parsed correctly."""
        source_file = selector.project_root / "src" / "notifications.py"
        source_file.parent.mkdir(parents=True, exist_ok=True)
        source_file.write_text(
            "# @spec FR-001: Fetch notifications — "
            ".specs/features/005-notifications/spec.md#fr-001\n",
            encoding="utf-8",
        )

        anchors = selector._parse_anchors_in_file(source_file)
        assert len(anchors) == 1
        assert anchors[0]["requirement_id"] == "FR"
        assert anchors[0]["spec_path"] == ".specs/features/005-notifications/spec.md"

    def test_multiple_anchors_parsed(self, selector: SmartTestSelector) -> None:
        """Multiple anchors in one file are all parsed."""
        source_file = selector.project_root / "src" / "multi.py"
        source_file.parent.mkdir(parents=True, exist_ok=True)
        source_file.write_text(
            "# @spec FR-001: First — .specs/features/005-notifications/spec.md#fr-001\n"
            "# @spec FR-002: Second — .specs/features/008-auth/spec.md#fr-002\n",
            encoding="utf-8",
        )

        anchors = selector._parse_anchors_in_file(source_file)
        assert len(anchors) == 2

    def test_stale_spec_path_skipped(self, selector: SmartTestSelector) -> None:
        """Stale spec references are skipped instead of producing bad mappings."""
        source_file = selector.project_root / "src" / "stale.py"
        source_file.parent.mkdir(parents=True, exist_ok=True)
        source_file.write_text(
            "# @spec FR-001: Stale — .specs/features/999-nonexistent/spec.md#fr-001\n",
            encoding="utf-8",
        )

        anchors = selector._parse_anchors_in_file(source_file)
        assert anchors == []


class TestFeatureExtraction:
    """Test feature slug extraction."""

    def test_feature_slug_extracted(self, selector: SmartTestSelector) -> None:
        """Feature slug is extracted from a valid spec path."""
        slug = selector._extract_feature_slug(".specs/features/005-notifications/spec.md")
        assert slug == "005-notifications"

    def test_invalid_spec_path_returns_none(self, selector: SmartTestSelector) -> None:
        """Invalid spec paths return `None`."""
        assert selector._extract_feature_slug("invalid/path/spec.md") is None


class TestHeuristicFallback:
    """Test filename heuristic fallback."""

    def test_keyword_match_in_filename(self, selector: SmartTestSelector) -> None:
        """Filename keywords can map a changed file back to a feature."""
        test_file = selector.project_root / "tests" / "notifications_test.py"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.touch()

        matches = selector._heuristic_feature_match(test_file)
        assert "005-notifications" in matches

    def test_no_match_returns_empty(self, selector: SmartTestSelector) -> None:
        """Unrelated files do not produce false matches."""
        test_file = selector.project_root / "tests" / "unrelated_test.py"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.touch()

        assert selector._heuristic_feature_match(test_file) == []

    def test_directory_keyword_match(self, selector: SmartTestSelector) -> None:
        """Parent directory keywords also participate in matching."""
        test_file = selector.project_root / "tests" / "auth" / "login_test.py"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.touch()

        matches = selector._heuristic_feature_match(test_file)
        assert "008-auth" in matches


class TestFeatureSetDetermination:
    """Test changed-file to feature resolution."""

    def test_single_file_single_feature(self, selector: SmartTestSelector) -> None:
        """One anchored file resolves to its feature."""
        source_file = selector.project_root / "src" / "notif.py"
        source_file.parent.mkdir(parents=True, exist_ok=True)
        source_file.write_text(
            "# @spec FR-001: Fetch — .specs/features/005-notifications/spec.md#fr-001\n",
            encoding="utf-8",
        )

        features = selector.from_changed_files([source_file])
        assert features == {"005-notifications"}

    def test_multiple_files_multiple_features(self, selector: SmartTestSelector) -> None:
        """Multiple anchored files produce the feature union."""
        file_one = selector.project_root / "src" / "notif.py"
        file_one.parent.mkdir(parents=True, exist_ok=True)
        file_one.write_text(
            "# @spec FR-001: Fetch — .specs/features/005-notifications/spec.md#fr-001\n",
            encoding="utf-8",
        )

        file_two = selector.project_root / "src" / "auth.py"
        file_two.write_text(
            "# @spec FR-001: Login — .specs/features/008-auth/spec.md#fr-001\n",
            encoding="utf-8",
        )

        features = selector.from_changed_files([file_one, file_two])
        assert features == {"005-notifications", "008-auth"}

    def test_fallback_heuristic_used_when_no_anchors(self, selector: SmartTestSelector) -> None:
        """Files without anchors use the filename heuristic."""
        test_file = selector.project_root / "tests" / "notifications_test.py"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("# Test file without anchors\n", encoding="utf-8")

        features = selector.from_changed_files([test_file])
        assert features == {"005-notifications"}


class TestTestResolution:
    """Test feature-to-test resolution."""

    def test_tests_for_features_reads_implementation(self, selector: SmartTestSelector) -> None:
        """Implementation docs provide explicit test targets."""
        refs = selector.tests_for_features({"005-notifications", "008-auth"})

        assert {ref["test_file"] for ref in refs} == {
            "tests/test_auth.py",
            "tests/test_notifications.py",
        }

    def test_tests_for_features_falls_back_to_scan(self, selector: SmartTestSelector) -> None:
        """Project test scans are used when explicit mappings are missing."""
        implementation_path = (
            selector.specs_root / "features" / "005-notifications" / "implementation.md"
        )
        implementation_path.unlink()
        fallback_test = selector.project_root / "tests" / "notifications_test.py"
        fallback_test.parent.mkdir(parents=True, exist_ok=True)
        fallback_test.write_text("def test_notifications() -> None:\n    pass\n", encoding="utf-8")

        refs = selector.tests_for_features({"005-notifications"})
        assert any(ref["test_file"] == "tests/notifications_test.py" for ref in refs)


class TestCacheOperations:
    """Test cache read and write behavior."""

    def test_cache_write_creates_file(self, selector: SmartTestSelector) -> None:
        """Writing the cache creates the expected file."""
        selector.cache = selector.build_cache()
        selector.write_cache()
        assert (selector.specs_root / ".test-selector-cache.json").exists()

    def test_cache_incremental_update(self, selector: SmartTestSelector) -> None:
        """Incremental updates preserve existing entries and add new ones."""
        old_file = selector.project_root / "src" / "old.py"
        old_file.parent.mkdir(parents=True, exist_ok=True)
        old_file.write_text(
            "# @spec FR-001: Old — .specs/features/005-notifications/spec.md#fr-001\n",
            encoding="utf-8",
        )
        selector.build_cache()
        selector.write_cache()

        new_file = selector.project_root / "src" / "new.py"
        new_file.write_text(
            "# @spec FR-001: New — .specs/features/008-auth/spec.md#fr-001\n",
            encoding="utf-8",
        )

        updated = selector.update_cache_incremental([new_file])
        assert "src/new.py" in updated["file_entries"]
        assert "src/old.py" in updated["file_entries"]

    def test_corrupted_cache_rebuilds(self, selector: SmartTestSelector) -> None:
        """Invalid JSON triggers a full cache rebuild."""
        source_file = selector.project_root / "src" / "test.py"
        source_file.parent.mkdir(parents=True, exist_ok=True)
        source_file.write_text(
            "# @spec FR-001: Fresh — .specs/features/005-notifications/spec.md#fr-001\n",
            encoding="utf-8",
        )
        selector.build_cache()
        (selector.specs_root / ".test-selector-cache.json").write_text(
            "{ invalid json",
            encoding="utf-8",
        )

        rebuilt = selector.update_cache_incremental([source_file])
        assert rebuilt["version"] == "1.0"
        assert "src/test.py" in rebuilt["file_entries"]


class TestGitIntegration:
    """Test git integration boundaries."""

    def test_baseline_discovery_fallback(self, selector: SmartTestSelector) -> None:
        """The baseline discovery falls back to `origin/main` when needed."""
        assert selector._discover_git_baseline() == "origin/main"

    def test_from_git_diff_uses_reported_files(
        self, monkeypatch: pytest.MonkeyPatch, selector: SmartTestSelector
    ) -> None:
        """Git diff output is routed through changed-file selection."""
        source_file = selector.project_root / "src" / "notif.py"
        source_file.parent.mkdir(parents=True, exist_ok=True)
        source_file.write_text(
            "# @spec FR-001: Fetch — .specs/features/005-notifications/spec.md#fr-001\n",
            encoding="utf-8",
        )

        def fake_run_git_command(args: list[str]) -> subprocess.CompletedProcess[str]:
            assert args == ["diff", "--cached", "--name-only"]
            return subprocess.CompletedProcess(
                args=["git", *args],
                returncode=0,
                stdout="src/notif.py\n",
                stderr="",
            )

        monkeypatch.setattr(selector, "_run_git_command", fake_run_git_command)
        assert selector.from_git_diff(staged=True) == {"005-notifications"}

    def test_from_git_diff_falls_back_on_error(
        self, monkeypatch: pytest.MonkeyPatch, selector: SmartTestSelector
    ) -> None:
        """A failed git diff falls back to the conservative full-suite scope."""

        def fake_run_git_command(args: list[str]) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(
                args=["git", *args],
                returncode=1,
                stdout="",
                stderr="fatal: bad revision",
            )

        monkeypatch.setattr(selector, "_run_git_command", fake_run_git_command)
        assert selector.from_git_diff(staged=True) == {
            "005-notifications",
            "008-auth",
        }


class TestErrorHandling:
    """Test resilience behavior."""

    def test_missing_spec_path_handled_gracefully(self, selector: SmartTestSelector) -> None:
        """Missing specs do not raise and do not invent impacted features."""
        source_file = selector.project_root / "src" / "broken.py"
        source_file.parent.mkdir(parents=True, exist_ok=True)
        source_file.write_text(
            "# @spec FR-001: Bad — .specs/features/999-missing/spec.md#fr-001\n",
            encoding="utf-8",
        )

        assert selector.from_changed_files([source_file]) == set()

    def test_binary_file_skipped(self, selector: SmartTestSelector) -> None:
        """Binary files are treated as non-matching inputs."""
        binary_file = selector.project_root / "image.png"
        binary_file.write_bytes(b"\x89PNG\r\n\x1a\n")
        assert selector.from_changed_files([binary_file]) == set()


class TestReporting:
    """Test reporting output."""

    def test_report_generation(self, selector: SmartTestSelector) -> None:
        """The report includes impacted features and selected test count."""
        report = selector.report_selection(
            {"005-notifications", "008-auth"},
            [
                {
                    "feature_id": "005-notifications",
                    "test_file": "tests/test_notifications.py",
                    "test_name": "",
                },
                {
                    "feature_id": "008-auth",
                    "test_file": "tests/test_auth.py",
                    "test_name": "",
                },
            ],
        )

        assert "005-notifications" in report
        assert "008-auth" in report
        assert "2 tests" in report
