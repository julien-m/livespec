#!/usr/bin/env python3
"""
audit-readme-status.py — Migration v9 helper.

Walks .specs/features/*/, infers the truthful Status column for each row
in .specs/README.md's Features table from artifacts on disk, and
regenerates the Recent Activity block from .specs/changelog.md.

Inputs (from migrate.sh): <project-dir> <livespec-dir>
The livespec-dir argument is unused — we only touch the project tree.
"""

from __future__ import annotations

import re
import sys
from datetime import date
from pathlib import Path
from typing import Final

FEATURES_START: Final[str] = "<!-- readme:features:start -->"
FEATURES_END: Final[str] = "<!-- readme:features:end -->"
ACTIVITY_START: Final[str] = "<!-- readme:activity:start -->"
ACTIVITY_END: Final[str] = "<!-- readme:activity:end -->"


IMPL_MARKERS = re.compile(
    # Match changelog phrases that indicate code shipped even if implementation.md
    # is missing because the feature predated the current bookkeeping flow.
    r"(implemented|implementation\b|spec\.implement|spec\.fix\s+gaps closed)",
    re.IGNORECASE,
)


def feature_changelog_says_implemented(feature_dir: Path) -> bool:
    """Return whether a feature changelog indicates the feature shipped.

    Args:
        feature_dir: Feature directory under ``.specs/features``.

    Returns:
        ``True`` when the feature changelog contains implementation markers.
    """
    changelog_path = feature_dir / "changelog.md"
    if not changelog_path.exists():
        return False
    try:
        changelog_text = changelog_path.read_text(encoding="utf-8")
    except OSError:
        return False
    return bool(IMPL_MARKERS.search(changelog_text))


PROMOTION_RANK: Final[dict[str, int]] = {
    "Draft": 0,
    "Planned": 1,
    "In Progress": 2,
    "Implemented": 3,
}


def infer_status(feature_dir: Path, current: str) -> str:
    """Infer the canonical README status for a feature directory.

    Args:
        feature_dir: Feature directory under ``.specs/features``.
        current: Current status value from the README row.

    Returns:
        The promoted status inferred from artifacts on disk.
    """
    if (feature_dir / "implementation.md").exists() or feature_changelog_says_implemented(
        feature_dir
    ):
        candidate = "Implemented"
    elif (feature_dir / "plan.md").exists():
        candidate = "Planned"
    else:
        candidate = "Draft"
    # Never downgrade a hand-curated status (e.g. user marked Implemented
    # when code was merged outside /spec-implement and impl.md is absent).
    cur_rank = PROMOTION_RANK.get(current.strip(), -1)
    new_rank = PROMOTION_RANK.get(candidate, -1)
    return candidate if new_rank > cur_rank else current.strip()


def feature_dirs(specs_root: Path) -> dict[str, Path]:
    """Return feature directories keyed by feature number.

    Args:
        specs_root: Root ``.specs`` directory for the project.

    Returns:
        Mapping from feature number such as ``004`` or ``005.1`` to directory.
    """
    directories: dict[str, Path] = {}
    features_root = specs_root / "features"
    if not features_root.is_dir():
        return directories
    for feature_path in sorted(features_root.iterdir()):
        if not feature_path.is_dir():
            continue
        feature_number_match = re.match(r"^(\d+(?:\.\d+)?)-", feature_path.name)
        if feature_number_match:
            directories[feature_number_match.group(1)] = feature_path
    return directories


def update_features_table(readme: str, dirs: dict[str, Path]) -> tuple[str, int]:
    """Rewrite README feature statuses from on-disk feature artifacts.

    Args:
        readme: Current README contents.
        dirs: Feature directory mapping keyed by feature number.

    Returns:
        Tuple of updated README contents and number of status changes applied.
    """
    if FEATURES_START not in readme or FEATURES_END not in readme:
        return readme, 0

    pre, rest = readme.split(FEATURES_START, 1)
    block, post = rest.split(FEATURES_END, 1)

    changed = 0
    # splitlines + join must round-trip a trailing newline if the original
    # block had one (it always does — markers sit on their own line).
    trailing_nl = block.endswith("\n")
    new_lines: list[str] = []
    for line in block.splitlines():
        m = re.match(r"^\|\s*([\d.]+)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|(.*)$", line)
        if not m:
            new_lines.append(line)
            continue
        nnn, name, current_status, tail = m.groups()
        if nnn not in dirs:
            new_lines.append(line)
            continue
        new_status = infer_status(dirs[nnn], current_status)
        if new_status == current_status.strip():
            new_lines.append(line)
            continue
        new_lines.append(f"| {nnn} | {name} | {new_status} |{tail}")
        changed += 1

    new_block = "\n".join(new_lines) + ("\n" if trailing_nl else "")
    return pre + FEATURES_START + new_block + FEATURES_END + post, changed


CHANGELOG_HEADING = re.compile(
    # Match `## YYYY-MM-DD - ...` or em-dash variants used in changelog headings.
    r"^##\s+(\d{4}-\d{2}-\d{2})\s*-{1,3}\s*(.+?)\s*$"
)


def parse_changelog_entries(changelog: Path, limit: int = 10) -> list[tuple[str, str, str]]:
    """Parse recent changelog headings into README activity rows.

    Args:
        changelog: Path to ``.specs/changelog.md``.
        limit: Maximum number of entries to return.

    Returns:
        Recent changelog entries in source order.
    """
    if not changelog.exists():
        return []
    entries: list[tuple[str, str, str]] = []
    for line in changelog.read_text(encoding="utf-8").splitlines():
        m = CHANGELOG_HEADING.match(line)
        if not m:
            continue
        d, raw = m.group(1), m.group(2)
        kind = classify_entry(raw)
        entries.append((d, kind, raw))
        if len(entries) >= limit:
            break
    return entries


def classify_entry(text: str) -> str:
    """Classify a changelog description into a README activity type.

    Args:
        text: Raw changelog heading text without the date prefix.

    Returns:
        Normalized activity type label for the README table.
    """
    low = text.lower()
    # Order matters: "Fix:" lines often mention "implementation.md" in their
    # description, so check fix patterns before the implementation match.
    if low.startswith("fix") or " fix:" in low or "fix:" in low:
        return "Fix"
    if "spec created" in low or low.startswith("spec:") or " spec " in low[:20]:
        return "Spec"
    if "implemented" in low or "implementation" in low:
        return "Feature"
    if "plan created" in low or low.startswith("plan:"):
        return "Plan"
    if "initialized" in low or low.startswith("setup"):
        return "Setup"
    return "Update"


def regenerate_activity(readme: str, entries: list[tuple[str, str, str]]) -> tuple[str, bool]:
    """Replace the README Recent Activity block with changelog-derived rows.

    Args:
        readme: Current README contents.
        entries: Parsed changelog entries for the activity table.

    Returns:
        Tuple of updated README contents and whether the block was regenerated.
    """
    if ACTIVITY_START not in readme or ACTIVITY_END not in readme:
        return readme, False
    pre, rest = readme.split(ACTIVITY_START, 1)
    _, post = rest.split(ACTIVITY_END, 1)

    rows = ["| Date | Type | Description |", "|---|---|---|"]
    for d, kind, desc in entries:
        rows.append(f"| {d} | {kind} | {desc} |")
    new_block = "\n" + "\n".join(rows) + "\n"
    return pre + ACTIVITY_START + new_block + ACTIVITY_END + post, True


def update_last_updated(readme: str, today: str) -> str:
    """Update the README header's ``Last updated`` line.

    Args:
        readme: Current README contents.
        today: ISO-formatted date to write into the header.

    Returns:
        README contents with the header date updated.
    """
    return re.sub(
        r"^(>\s*Last updated:\s*).*$",
        rf"\g<1>{today}",
        readme,
        count=1,
        flags=re.MULTILINE,
    )


def main(argv: list[str]) -> int:
    """Run the README status audit for a target project directory.

    Args:
        argv: CLI arguments where ``argv[1]`` is the project directory.

    Returns:
        Process exit code.
    """
    if len(argv) < 2:
        print("Usage: audit-readme-status.py <project-dir> [<livespec-dir>]", file=sys.stderr)
        return 2
    project_dir = Path(argv[1]).resolve()
    specs_root = project_dir / ".specs"
    readme_path = specs_root / "README.md"
    changelog_path = specs_root / "changelog.md"

    if not readme_path.exists():
        print(f"  ▸ {readme_path.relative_to(project_dir)} not found — skipping audit")
        return 0

    original = readme_path.read_text(encoding="utf-8")
    dirs = feature_dirs(specs_root)
    updated, status_changes = update_features_table(original, dirs)

    entries = parse_changelog_entries(changelog_path, limit=10)
    updated, activity_changed = regenerate_activity(updated, entries)

    if status_changes or activity_changed:
        updated = update_last_updated(updated, date.today().isoformat())

    if updated != original:
        readme_path.write_text(updated, encoding="utf-8")
        activity_result = (
            "activity regenerated" if activity_changed else "activity unchanged"
        )
        print(
            f"  ▸ README audit: {status_changes} status correction(s), {activity_result}"
        )
    else:
        print("  ▸ README audit: nothing to fix")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
