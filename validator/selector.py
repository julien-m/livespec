"""Smart test selector for mapping changed files to impacted tests.

@spec FR-001: Implement SmartTestSelector class — .specs/features/033-smart-test-selection/spec.md#fr-001
@spec FR-002: Implement @spec anchor parser — .specs/features/033-smart-test-selection/spec.md#fr-002
@spec FR-003: Implement test target resolution — .specs/features/033-smart-test-selection/spec.md#fr-003
@spec FR-004: Implement filename heuristic fallback — .specs/features/033-smart-test-selection/spec.md#fr-004
@spec FR-005: Implement cache read/write/incremental update — .specs/features/033-smart-test-selection/spec.md#fr-005
"""

import json
import logging
import re
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import TypedDict

logger = logging.getLogger(__name__)


class AnchorRecord(TypedDict):
    """Parsed `@spec` anchor metadata."""

    requirement_id: str
    spec_path: str


class CacheEntry(TypedDict):
    """Cached anchors for one source file."""

    mtime: float
    anchors: list[AnchorRecord]


class TestReference(TypedDict):
    """Resolved test target for an impacted feature."""

    feature_id: str
    test_file: str
    test_name: str


class CacheData(TypedDict):
    """Serialized cache payload."""

    version: str
    generated_at: str
    elapsed_ms: float
    file_entries: dict[str, CacheEntry]


class SmartTestSelector:
    """Resolve impacted features and tests from changed files."""

    # This regex extracts `@spec` anchors that link back to feature spec files.
    ANCHOR_PATTERN = re.compile(
        r"@spec\s+(?P<req_id>FR|AC)-\d{3}.*?—\s*"
        r"(?P<spec_path>\.specs/features/\d{3}-[a-z0-9-]+/spec\.md)"
        r"#(?:fr|ac)-\d{3}",
        re.MULTILINE,
    )
    FEATURE_PATTERN = re.compile(r"\.specs/features/(\d{3}-[a-z0-9-]+)/spec\.md")
    TEST_FILE_PATTERN = re.compile(r"(tests/[^\s`|]+(?:test|spec)\.(?:py|ts|js|go|rs|java|kt))")
    CACHE_FILENAME = ".test-selector-cache.json"
    CACHE_SCHEMA_VERSION = "1.0"
    SOURCE_SUFFIXES = {
        ".c",
        ".cpp",
        ".go",
        ".h",
        ".java",
        ".js",
        ".jsx",
        ".kt",
        ".m",
        ".py",
        ".rs",
        ".sh",
        ".sql",
        ".swift",
        ".ts",
        ".tsx",
    }
    EXCLUDED_PARTS = {
        ".git",
        ".pytest_cache",
        ".venv",
        "__pycache__",
        "build",
        "dist",
        "node_modules",
        "venv",
    }
    TEST_FILE_SUFFIXES = {".go", ".js", ".py", ".rs", ".ts"}

    def __init__(self, specs_root: Path | str) -> None:
        """Initialize the selector.

        Args:
            specs_root: Path to the project's `.specs` directory.
        """
        self.specs_root = Path(specs_root)
        self.project_root = self.specs_root.parent
        self.cache_path = self.specs_root / self.CACHE_FILENAME
        self.cache: CacheData = self._empty_cache()

    def from_changed_files(self, files: list[Path | str]) -> set[str]:
        """Resolve impacted feature slugs from changed files.

        Args:
            files: Changed file paths, relative to the project root or absolute.

        Returns:
            The deduplicated set of impacted feature slugs.
        """
        features: set[str] = set()
        fallback_files: list[Path] = []

        for file_path in files:
            path = self._normalize_to_project_path(file_path)
            anchors = self._parse_anchors_in_file(path)
            if anchors:
                for anchor in anchors:
                    feature_slug = self._extract_feature_slug(anchor["spec_path"])
                    if feature_slug is not None:
                        features.add(feature_slug)
                continue

            fallback_files.append(path)

        for path in fallback_files:
            heuristic_matches = self._heuristic_feature_match(path)
            if heuristic_matches:
                logger.info(
                    "Fallback (AC-003): no @spec anchors in %s -> matched %s tests",
                    path,
                    ", ".join(heuristic_matches),
                )
                features.update(heuristic_matches)

        return features

    def tests_for_features(self, feature_ids: set[str]) -> list[TestReference]:
        """Resolve test targets for the provided features.

        Args:
            feature_ids: Impacted feature slugs.

        Returns:
            Deduplicated test references gathered from `implementation.md` files
            or a fallback project test scan.
        """
        test_refs: list[TestReference] = []
        seen: set[tuple[str, str]] = set()

        for feature_id in sorted(feature_ids):
            refs = self._test_refs_for_feature(feature_id)
            for ref in refs:
                ref_key = (ref["test_file"], ref["test_name"])
                if ref_key not in seen:
                    test_refs.append(ref)
                    seen.add(ref_key)

        return test_refs

    def build_cache(self) -> CacheData:
        """Rebuild the anchor cache from scratch.

        Returns:
            The newly built cache payload.
        """
        start_time = time.perf_counter()
        file_entries: dict[str, CacheEntry] = {}

        for source_file in self.project_root.rglob("*"):
            if not source_file.is_file() or not self._is_source_file(source_file):
                continue

            anchors = self._parse_anchors_in_file(source_file)
            if not anchors:
                continue

            relative_path = self._relative_to_project(source_file)
            file_entries[relative_path] = {
                "mtime": source_file.stat().st_mtime,
                "anchors": anchors,
            }

        elapsed_ms = (time.perf_counter() - start_time) * 1000
        self.cache = {
            "version": self.CACHE_SCHEMA_VERSION,
            "generated_at": datetime.now(UTC).isoformat(),
            "elapsed_ms": elapsed_ms,
            "file_entries": file_entries,
        }
        logger.info("Cache built in %.0f ms", elapsed_ms)
        return self.cache

    def update_cache_incremental(self, changed_files: list[Path | str]) -> CacheData:
        """Refresh cache entries for the provided changed files.

        Args:
            changed_files: Changed file paths, relative to the project root or absolute.

        Returns:
            The updated cache payload.
        """
        start_time = time.perf_counter()
        cache_data = self._load_cache()
        file_entries = dict(cache_data["file_entries"])

        for changed_file in changed_files:
            path = self._normalize_to_project_path(changed_file)
            relative_path = self._relative_to_project(path)

            if not path.exists() or not path.is_file():
                file_entries.pop(relative_path, None)
                continue

            anchors = self._parse_anchors_in_file(path)
            if anchors:
                file_entries[relative_path] = {
                    "mtime": path.stat().st_mtime,
                    "anchors": anchors,
                }
                continue

            file_entries.pop(relative_path, None)

        elapsed_ms = (time.perf_counter() - start_time) * 1000
        self.cache = {
            "version": self.CACHE_SCHEMA_VERSION,
            "generated_at": datetime.now(UTC).isoformat(),
            "elapsed_ms": elapsed_ms,
            "file_entries": file_entries,
        }
        logger.info("Cache updated in %.0f ms", elapsed_ms)
        return self.cache

    def write_cache(self) -> None:
        """Persist the in-memory cache to disk."""
        self.cache_path.write_text(
            json.dumps(self.cache, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    def from_git_diff(self, ref: str | None = None, staged: bool = False) -> set[str]:
        """Resolve impacted features from the git diff.

        Args:
            ref: Optional git ref used as the diff baseline.
            staged: When `True`, use the staged diff for pre-commit flows.

        Returns:
            The deduplicated set of impacted feature slugs.
        """
        try:
            if staged:
                # The staged diff is the pre-commit contract: only inspect files
                # queued for the next commit, not the working tree.
                result = self._run_git_command(["diff", "--cached", "--name-only"])
            elif ref is not None:
                result = self._run_git_command(["diff", f"{ref}..HEAD", "--name-only"])
            else:
                baseline = self._discover_git_baseline()
                result = self._run_git_command(["diff", f"{baseline}..HEAD", "--name-only"])
        except OSError as exc:
            logger.warning(
                "AC-010: git is unavailable (%s). Running the full test suite.",
                exc,
            )
            return self._get_all_features()

        if result.returncode != 0:
            logger.warning(
                "AC-010: git diff failed (%s). Running the full test suite.",
                result.stderr.strip(),
            )
            return self._get_all_features()

        changed_files = [Path(line) for line in result.stdout.splitlines() if line.strip()]
        return self.from_changed_files(changed_files)

    def report_selection(self, feature_ids: set[str], test_refs: list[TestReference]) -> str:
        """Build a human-readable summary of the selected scope.

        Args:
            feature_ids: Impacted feature slugs.
            test_refs: Resolved test references.

        Returns:
            A short report summarizing the selection.
        """
        features_str = ", ".join(sorted(feature_ids)) or "none"
        test_count = len(test_refs)
        all_feature_count = len(self._get_all_features())
        # This uses a coarse per-feature average because the selector currently
        # reports scope size, not a precomputed exact full-suite test inventory.
        skipped_count = max(0, all_feature_count * 100 - test_count)
        return (
            f"Impacted features: {features_str}. "
            f"Running {test_count} tests (skipped ~{skipped_count} tests)."
        )

    def _parse_anchors_in_file(self, path: Path) -> list[AnchorRecord]:
        """Parse all `@spec` anchors from one source file.

        Args:
            path: Source file path.

        Returns:
            Parsed anchors. Invalid or stale anchors are ignored.
        """
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return []

        anchors: list[AnchorRecord] = []
        for match in self.ANCHOR_PATTERN.finditer(content):
            spec_path = match.group("spec_path")
            resolved_spec_path = self._resolve_spec_path(spec_path)
            if not resolved_spec_path.exists():
                logger.warning(
                    "AC-010: stale @spec anchor in %s references missing %s. Skipping.",
                    path,
                    spec_path,
                )
                continue

            anchors.append(
                {
                    "requirement_id": match.group("req_id"),
                    "spec_path": spec_path,
                }
            )

        return anchors

    def _extract_feature_slug(self, spec_path: str) -> str | None:
        """Extract the feature slug from a spec path.

        Args:
            spec_path: Path embedded in an `@spec` anchor.

        Returns:
            The `NNN-slug` feature identifier when present.
        """
        match = self.FEATURE_PATTERN.search(spec_path)
        if match is None:
            return None
        return match.group(1)

    def _heuristic_feature_match(self, file_path: Path) -> list[str]:
        """Fall back to filename and directory keywords when anchors are absent.

        Args:
            file_path: Changed file path.

        Returns:
            Matching feature slugs.
        """
        filename = file_path.name.lower()
        parent_dir = file_path.parent.name.lower()
        features_dir = self.specs_root / "features"
        if not features_dir.exists():
            return []

        matches: list[str] = []
        for feature_dir in sorted(features_dir.iterdir()):
            if not feature_dir.is_dir():
                continue

            slug = feature_dir.name
            keywords = slug.split("-")[1:]
            if any(keyword in filename or keyword in parent_dir for keyword in keywords):
                matches.append(slug)

        return matches

    def _extract_test_refs_from_impl(
        self, impl_content: str, feature_id: str
    ) -> list[TestReference]:
        """Extract explicit test file references from `implementation.md`.

        Args:
            impl_content: Raw markdown content.
            feature_id: Feature slug owning the implementation document.

        Returns:
            Resolved test references found in the markdown.
        """
        refs: list[TestReference] = []
        for match in self.TEST_FILE_PATTERN.finditer(impl_content):
            refs.append(
                {
                    "feature_id": feature_id,
                    "test_file": match.group(1),
                    "test_name": "",
                }
            )
        return refs

    def _scan_test_directory(self, feature_id: str) -> list[TestReference]:
        """Scan common test directories when no explicit mapping is available.

        Args:
            feature_id: Feature slug whose tests should be resolved.

        Returns:
            Fallback test references.
        """
        refs: list[TestReference] = []
        feature_dir = self.specs_root / "features" / feature_id
        test_dirs = [feature_dir / "tests", self.project_root / "tests"]

        for test_dir in test_dirs:
            if not test_dir.exists():
                continue

            for test_file in test_dir.rglob("*test.*"):
                if test_file.suffix not in self.TEST_FILE_SUFFIXES:
                    continue

                refs.append(
                    {
                        "feature_id": feature_id,
                        "test_file": self._relative_to_project(test_file),
                        "test_name": "",
                    }
                )

        return refs

    def _discover_git_baseline(self) -> str:
        """Discover the default baseline for pre-push selection.

        Returns:
            A git ref suitable for `git diff <baseline>..HEAD`.
        """
        try:
            remote_head = self._run_git_command(["rev-parse", "--abbrev-ref", "origin/HEAD"])
            if remote_head.returncode == 0 and remote_head.stdout.strip():
                return remote_head.stdout.strip()
        except OSError:
            logger.debug("Failed to resolve origin/HEAD; falling back to origin/main.")

        return "origin/main"

    def _get_all_features(self) -> set[str]:
        """Return every feature slug under `.specs/features`.

        Returns:
            All known feature slugs.
        """
        features_dir = self.specs_root / "features"
        if not features_dir.exists():
            return set()

        return {feature_dir.name for feature_dir in features_dir.iterdir() if feature_dir.is_dir()}

    def _is_source_file(self, path: Path) -> bool:
        """Check whether a path should be scanned for anchors.

        Args:
            path: Candidate source file.

        Returns:
            `True` when the file should be scanned.
        """
        if any(part in self.EXCLUDED_PARTS for part in path.parts):
            return False
        return path.suffix in self.SOURCE_SUFFIXES

    def _test_refs_for_feature(self, feature_id: str) -> list[TestReference]:
        """Resolve test references for one feature.

        Args:
            feature_id: Feature slug to inspect.

        Returns:
            Explicit or fallback test references.
        """
        implementation_path = self.specs_root / "features" / feature_id / "implementation.md"
        if implementation_path.exists():
            try:
                content = implementation_path.read_text(encoding="utf-8")
            except OSError as exc:
                logger.warning(
                    "EC-003: could not read %s (%s). Falling back to directory scan.",
                    implementation_path,
                    exc,
                )
            else:
                refs = self._extract_test_refs_from_impl(content, feature_id)
                if refs:
                    return refs

        logger.debug(
            "EC-003: no explicit implementation mapping for %s. Using directory scan.",
            feature_id,
        )
        return self._scan_test_directory(feature_id)

    def _load_cache(self) -> CacheData:
        """Load the on-disk cache or rebuild it when invalid.

        Returns:
            A valid cache payload.
        """
        if not self.cache_path.exists():
            return self.build_cache()

        try:
            raw_cache = json.loads(self.cache_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("EC-005: cache is invalid (%s). Rebuilding from scratch.", exc)
            return self.build_cache()

        try:
            file_entries = raw_cache["file_entries"]
            generated_at = raw_cache["generated_at"]
            elapsed_ms = float(raw_cache.get("elapsed_ms", 0.0))
            version = str(raw_cache["version"])
        except (KeyError, TypeError, ValueError) as exc:
            logger.warning(
                "EC-005: cache schema is invalid (%s). Rebuilding from scratch.",
                exc,
            )
            return self.build_cache()

        self.cache = {
            "version": version,
            "generated_at": str(generated_at),
            "elapsed_ms": elapsed_ms,
            "file_entries": self._coerce_cache_entries(file_entries),
        }
        return self.cache

    def _coerce_cache_entries(self, raw_entries: object) -> dict[str, CacheEntry]:
        """Normalize decoded JSON into typed cache entries.

        Args:
            raw_entries: JSON-decoded `file_entries` payload.

        Returns:
            Typed cache entries.
        """
        if not isinstance(raw_entries, dict):
            return {}

        entries: dict[str, CacheEntry] = {}
        for path_key, raw_entry in raw_entries.items():
            if not isinstance(path_key, str) or not isinstance(raw_entry, dict):
                continue

            raw_mtime = raw_entry.get("mtime")
            raw_anchors = raw_entry.get("anchors")
            if not isinstance(raw_mtime, (int, float)) or not isinstance(raw_anchors, list):
                continue

            anchors: list[AnchorRecord] = []
            for raw_anchor in raw_anchors:
                if not isinstance(raw_anchor, dict):
                    continue

                requirement_id = raw_anchor.get("requirement_id")
                spec_path = raw_anchor.get("spec_path")
                if isinstance(requirement_id, str) and isinstance(spec_path, str):
                    anchors.append(
                        {
                            "requirement_id": requirement_id,
                            "spec_path": spec_path,
                        }
                    )

            entries[path_key] = {"mtime": float(raw_mtime), "anchors": anchors}

        return entries

    def _resolve_spec_path(self, spec_path: str) -> Path:
        """Resolve an anchor spec path against the project root.

        Args:
            spec_path: Project-relative spec path stored in source anchors.

        Returns:
            Absolute path to the referenced spec file.
        """
        relative_path = Path(spec_path)
        if relative_path.parts and relative_path.parts[0] == ".specs":
            return self.project_root / relative_path
        return self.specs_root / relative_path

    def _normalize_to_project_path(self, file_path: Path | str) -> Path:
        """Convert a relative path into an absolute project path.

        Args:
            file_path: Path from git or caller code.

        Returns:
            Absolute path rooted in the project.
        """
        path = Path(file_path)
        if path.is_absolute():
            return path
        return self.project_root / path

    def _relative_to_project(self, path: Path) -> str:
        """Convert an absolute project path into a stable relative path.

        Args:
            path: Project file path.

        Returns:
            Relative path string when possible, otherwise the original string form.
        """
        try:
            return str(path.relative_to(self.project_root))
        except ValueError:
            return str(path)

    def _run_git_command(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        """Run one git command inside the project root.

        Args:
            args: Arguments after the `git` executable.

        Returns:
            The completed subprocess result.
        """
        # Git is the selector boundary with the outside world; callers rely on
        # stdout containing one path per line and a non-zero exit code on failure.
        return subprocess.run(
            ["git", *args],
            capture_output=True,
            text=True,
            cwd=self.project_root,
            check=False,
        )

    def _empty_cache(self) -> CacheData:
        """Create an empty cache payload.

        Returns:
            Empty cache data matching the serialized schema.
        """
        return {
            "version": self.CACHE_SCHEMA_VERSION,
            "generated_at": "",
            "elapsed_ms": 0.0,
            "file_entries": {},
        }
