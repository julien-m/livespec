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


FEATURES_START = "<!-- readme:features:start -->"
FEATURES_END = "<!-- readme:features:end -->"
ACTIVITY_START = "<!-- readme:activity:start -->"
ACTIVITY_END = "<!-- readme:activity:end -->"


IMPL_MARKERS = re.compile(
    r"(implemented|implementation\b|spec\.implement|spec\.fix\s+gaps closed)",
    re.IGNORECASE,
)


def feature_changelog_says_implemented(feature_dir: Path) -> bool:
    """A feature's own changelog mentioning implementation/fix activity is
    a strong signal that code shipped, even if implementation.md is missing
    (e.g., feature merged through a PR before /spec.implement bookkeeping)."""
    cl = feature_dir / "changelog.md"
    if not cl.exists():
        return False
    try:
        text = cl.read_text(encoding="utf-8")
    except OSError:
        return False
    return bool(IMPL_MARKERS.search(text))


PROMOTION_RANK = {"Draft": 0, "Planned": 1, "In Progress": 2, "Implemented": 3}


def infer_status(feature_dir: Path, current: str) -> str:
    if (feature_dir / "implementation.md").exists():
        candidate = "Implemented"
    elif feature_changelog_says_implemented(feature_dir):
        candidate = "Implemented"
    elif (feature_dir / "plan.md").exists():
        candidate = "Planned"
    else:
        candidate = "Draft"
    # Never downgrade a hand-curated status (e.g. user marked Implemented
    # when code was merged outside /spec.implement and impl.md is absent).
    cur_rank = PROMOTION_RANK.get(current.strip(), -1)
    new_rank = PROMOTION_RANK.get(candidate, -1)
    return candidate if new_rank > cur_rank else current.strip()


def feature_dirs(specs_root: Path) -> dict[str, Path]:
    """Map feature number (e.g. '004', '005.1') → directory."""
    out: dict[str, Path] = {}
    features_root = specs_root / "features"
    if not features_root.is_dir():
        return out
    for d in sorted(features_root.iterdir()):
        if not d.is_dir():
            continue
        m = re.match(r"^(\d+(?:\.\d+)?)-", d.name)
        if m:
            out[m.group(1)] = d
    return out


def update_features_table(readme: str, dirs: dict[str, Path]) -> tuple[str, int]:
    """Rewrite the Status column for each row whose # matches a feature dir."""
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


CHANGELOG_HEADING = re.compile(r"^##\s+(\d{4}-\d{2}-\d{2})\s*-{1,3}\s*(.+?)\s*$")


def parse_changelog_entries(changelog: Path, limit: int = 10) -> list[tuple[str, str, str]]:
    """Return [(date, type, description), ...] in changelog order (most recent first)."""
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
    low = text.lower()
    if "spec created" in low or low.startswith("spec:") or " spec " in low[:20]:
        return "Spec"
    if "implemented" in low or "implementation" in low:
        return "Feature"
    if "plan created" in low or low.startswith("plan:"):
        return "Plan"
    if low.startswith("fix") or " fix:" in low or "fix:" in low:
        return "Fix"
    if "initialized" in low or low.startswith("setup"):
        return "Setup"
    return "Update"


def regenerate_activity(readme: str, entries: list[tuple[str, str, str]]) -> tuple[str, bool]:
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
    return re.sub(r"^(>\s*Last updated:\s*).*$", rf"\g<1>{today}", readme, count=1, flags=re.MULTILINE)


def main(argv: list[str]) -> int:
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
        print(f"  ▸ README audit: {status_changes} status correction(s), "
              f"{'activity regenerated' if activity_changed else 'activity unchanged'}")
    else:
        print("  ▸ README audit: nothing to fix")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
