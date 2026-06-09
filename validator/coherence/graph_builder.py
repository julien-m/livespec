"""Build the SpecGraph from .specs/ on disk."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

import frontmatter
import yaml


@dataclass
class RoadmapItem:
    """A single item from the roadmap checklist."""

    name: str
    slug: str
    checked: bool
    link: str | None
    line_number: int


@dataclass
class FeatureInfo:
    """Metadata for a single feature directory."""

    dir_name: str
    num: int
    slug: str
    files: dict[str, bool] = field(default_factory=dict)
    status: str | None = None
    spec_anchors: list[str] = field(default_factory=list)
    spec_mtime: float | None = None
    implementation_paths: dict[str, list[str]] = field(default_factory=dict)


@dataclass
class SpecGraph:
    """Graph of all spec artifacts and their relationships.

    Attributes:
        roadmap: Parsed roadmap.md checklist items and feature references.
        features: All features extracted from features/ directory.
        readme_entries: Section headers and links found in README.md.
        readme_statuses: Status badges and their corresponding feature numbers.
        stack_technologies: Technology choices and version pins from stack.md.
        preflight_checks: Preflight checks from stack.md.
        changelog_refs: Feature references found in changelog.md.
    """

    roadmap: list[RoadmapItem] = field(default_factory=list)
    features: list[FeatureInfo] = field(default_factory=list)
    readme_entries: list[str] = field(default_factory=list)
    readme_statuses: dict[str, str] = field(default_factory=dict)
    stack_technologies: list[str] = field(default_factory=list)
    preflight_checks: list[str] = field(default_factory=list)
    changelog_refs: list[str] = field(default_factory=list)

    def get_feature(self, dir_name: str) -> FeatureInfo | None:
        """Find a feature by directory name.

        Args:
            dir_name: Feature directory name to search for.

        Returns:
            FeatureInfo if found, None otherwise.
        """
        for feature in self.features:
            if feature.dir_name == dir_name:
                return feature
        return None

    @property
    def feature_dirs(self) -> set[str]:
        """Set of all feature directory names."""
        return {feature.dir_name for feature in self.features}


# Regex for roadmap checklist items
_CHECKLIST_RE = re.compile(r"^- \[([ xX])\]\s+(?:\[([^\]]+)\]\(([^)]+)\)|(.+))$", re.MULTILINE)

# Regex for embedded feature links inside richer roadmap item copy.
_FEATURE_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]*features/[^)]+)\)")

# Regex for feature dir names (NNN-slug) and legacy sub-feature dirs (NNN.M-slug).
_FEATURE_DIR_RE = re.compile(r"^(\d+(?:\.\d+)?)-(.+)$")

# Regex for @spec anchors (FR-xxx, AC-xxx)
_SPEC_ANCHOR_RE = re.compile(r"@spec\(?((?:FR|AC)-\d+)\)?")

# Markdown table rows with pipe-delimited cells.
_TABLE_ROW_RE = re.compile(r"^\|(.+)\|$")

# Backticked file paths inside implementation map cells.
_BACKTICK_PATH_RE = re.compile(r"`([^`]+)`")

# Implementation map requirement identifiers.
_REQ_RE = re.compile(r"^(?:FR|AC)-\d+$")

_PATH_SUFFIXES = {
    ".css",
    ".html",
    ".ini",
    ".java",
    ".js",
    ".json",
    ".kt",
    ".lock",
    ".md",
    ".pdf",
    ".pen",
    ".png",
    ".py",
    ".rs",
    ".sh",
    ".swift",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".yaml",
    ".yml",
}


def _parse_roadmap(specs_root: Path) -> list[RoadmapItem]:
    """Parse roadmap.md for checklist items."""
    roadmap_path = specs_root / "roadmap.md"
    if not roadmap_path.exists():
        return []

    content = roadmap_path.read_text()
    items: list[RoadmapItem] = []

    for line_number, line in enumerate(content.splitlines(), 1):
        match = _CHECKLIST_RE.match(line.strip())
        if not match:
            continue

        checked = match.group(1) in ("x", "X")
        if match.group(2):  # [name](link)
            name = match.group(2)
            link = match.group(3)
        else:
            name = match.group(4).strip()
            link = None
            embedded_link = _FEATURE_LINK_RE.search(name)
            if embedded_link:
                link = embedded_link.group(2)

        # Extract slug from link or name
        slug = name
        if link and "features/" in link:
            parts = link.split("features/")[-1].split("/")[0]
            slug = parts

        items.append(
            RoadmapItem(name=name, slug=slug, checked=checked, link=link, line_number=line_number)
        )

    return items


def _parse_features(specs_root: Path) -> list[FeatureInfo]:
    """Scan features/ directory for feature info."""
    features_dir = specs_root / "features"
    if not features_dir.exists():
        return []

    features: list[FeatureInfo] = []
    expected_files = ["spec", "plan", "implementation", "progress", "changelog"]

    for d in sorted(features_dir.iterdir()):
        if not d.is_dir():
            continue

        m = _FEATURE_DIR_RE.match(d.name)
        if not m:
            continue

        num = int(m.group(1).split(".", 1)[0])
        slug = m.group(2)

        files = {name: (d / f"{name}.md").exists() for name in expected_files}

        # Read spec.md frontmatter for status
        status = None
        spec_mtime = None
        spec_path = d / "spec.md"
        if spec_path.exists():
            spec_mtime = spec_path.stat().st_mtime
            try:
                post = frontmatter.load(str(spec_path))
                raw_status = post.metadata.get("status")
                status = raw_status if isinstance(raw_status, str) else None
            except (yaml.YAMLError, OSError) as exc:
                logging.warning("Failed to parse %s: %s", spec_path, exc)

        # Read implementation.md for @spec anchors and file paths
        spec_anchors: list[str] = []
        impl_paths: dict[str, list[str]] = {}
        impl_path = d / "implementation.md"
        if impl_path.exists():
            try:
                impl_content = impl_path.read_text()
                spec_anchors = _SPEC_ANCHOR_RE.findall(impl_content)
                for line in impl_content.splitlines():
                    if not _TABLE_ROW_RE.match(line.strip()) or "---" in line:
                        continue
                    cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
                    if not cells or not _REQ_RE.match(cells[0]):
                        continue
                    anchor_id = cells[0]
                    for file_path in _extract_paths_from_cells(cells[1:]):
                        impl_paths.setdefault(anchor_id, []).append(file_path)
            except (yaml.YAMLError, OSError) as exc:
                logging.warning("Failed to read %s: %s", impl_path, exc)

        features.append(
            FeatureInfo(
                dir_name=d.name,
                num=num,
                slug=slug,
                files=files,
                status=status,
                spec_anchors=spec_anchors,
                spec_mtime=spec_mtime,
                implementation_paths=impl_paths,
            )
        )

    return features


def _parse_readme(specs_root: Path) -> tuple[list[str], dict[str, str]]:
    """Parse .specs/README.md for feature references and statuses."""
    readme_path = specs_root / "README.md"
    if not readme_path.exists():
        return [], {}

    content = readme_path.read_text()
    entries: list[str] = []
    statuses: dict[str, str] = {}

    # Look for table rows or links referencing features/NNN-name
    feature_link_re = re.compile(r"features/(\d+(?:\.\d+)?-[^/)\s|]+)")
    status_re = re.compile(
        r"\|\s*\[?(?:features/)?(\d+(?:\.\d+)?-[^/)\]\s|]+)\]?[^|]*"
        r"\|\s*(\w[\w\s]*?)\s*\|"
    )

    for line in content.splitlines():
        for m in feature_link_re.finditer(line):
            dir_name = m.group(1).rstrip("/")
            if dir_name not in entries:
                entries.append(dir_name)

        sm = status_re.match(line)
        if sm:
            statuses[sm.group(1)] = sm.group(2).strip()

    return entries, statuses


def _parse_stack(specs_root: Path) -> list[str]:
    """Extract technology names from stacks/_default.md."""
    stack_path = specs_root / "stacks" / "_default.md"
    if not stack_path.exists():
        return []

    content = stack_path.read_text()
    # Extract items from bullet lists under ## Stack
    techs: list[str] = []
    in_stack = False
    for line in content.splitlines():
        if line.startswith("## ") and "stack" in line.lower():
            in_stack = True
            continue
        if line.startswith("## ") and in_stack:
            break
        if in_stack and line.strip().startswith("- "):
            # Extract first word/phrase (technology name)
            text = line.strip().lstrip("- ").split(":")[0].split("(")[0].strip()
            if text:
                techs.append(text)

    return techs


def _parse_preflight(specs_root: Path) -> list[str]:
    """Extract check items from preflight.md or preflight-report.md."""
    for name in ("preflight.md", "preflight-report.md"):
        path = specs_root / name
        if path.exists():
            content = path.read_text()
            checks: list[str] = []
            for line in content.splitlines():
                if line.strip().startswith("- "):
                    checks.append(line.strip().lstrip("- ").strip())
            return checks
    return []


def _parse_changelog(specs_root: Path) -> list[str]:
    """Extract feature references from changelog.md."""
    changelog_path = specs_root / "changelog.md"
    if not changelog_path.exists():
        return []

    content = changelog_path.read_text()
    refs: list[str] = []
    feature_ref_re = re.compile(r"\b(\d{3}-[a-z0-9][a-z0-9-]*)\b")

    for line in content.splitlines():
        for m in feature_ref_re.finditer(line):
            ref = m.group(1)
            if ref not in refs:
                refs.append(ref)

    return refs


def _extract_paths_from_cells(cells: list[str]) -> list[str]:
    """Extract plausible implementation paths from Markdown table cells."""
    paths: list[str] = []
    for cell in cells:
        backticked_values = _BACKTICK_PATH_RE.findall(cell)
        raw_values = backticked_values or [cell]
        for raw_value in raw_values:
            for value in re.split(r",|\n", raw_value):
                cleaned = value.strip().strip("`")
                if _looks_like_path(cleaned, explicit=bool(backticked_values)):
                    paths.append(cleaned)
    return paths


def _looks_like_path(value: str, *, explicit: bool) -> bool:
    """Return True when a table value resembles a file or glob path."""
    if (
        not value
        or value.startswith(("@spec", "#", "/spec.", "/spec-"))
        or value in {".reserved", ".specs/.LOCK"}
    ):
        return False
    if any(token in value for token in ("(", ")", "{", "}", "[feature]")):
        return False
    if any(char.isspace() for char in value):
        return False
    path_part = value.split("::", 1)[0]
    if "/" in path_part or path_part.startswith("."):
        return True
    if explicit:
        return Path(path_part).suffix.lower() in _PATH_SUFFIXES
    return False


def build_graph(specs_root: Path) -> SpecGraph:
    """Build the complete SpecGraph from .specs/ on disk.

    Args:
        specs_root: Root directory of the .specs/ tree.

    Returns:
        SpecGraph containing all parsed artifacts and their relationships.
    """
    roadmap = _parse_roadmap(specs_root)
    features = _parse_features(specs_root)
    readme_entries, readme_statuses = _parse_readme(specs_root)
    stack_techs = _parse_stack(specs_root)
    preflight_checks = _parse_preflight(specs_root)
    changelog_refs = _parse_changelog(specs_root)

    return SpecGraph(
        roadmap=roadmap,
        features=features,
        readme_entries=readme_entries,
        readme_statuses=readme_statuses,
        stack_technologies=stack_techs,
        preflight_checks=preflight_checks,
        changelog_refs=changelog_refs,
    )
