"""Auto-fix Pass 1 — deterministic mechanical corrections."""

from __future__ import annotations

import logging
import re
import shutil
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

import frontmatter
import yaml

from .config import ValidatorConfig, resolve_file_type
from .engine import FileResult, validate_file


@dataclass
class FixAction:
    """Description of a single fix applied."""

    file: Path
    description: str
    field: str | None = None


VALID_STATUSES = {"Draft", "Review", "Approved", "Implemented", "Deprecated"}
VALID_PRIORITIES = {"P1", "P2", "P3"}

ROADMAP_MARKERS = [
    ("<!-- roadmap:mvp:start -->", "<!-- roadmap:mvp:end -->"),
    ("<!-- roadmap:postmvp:start -->", "<!-- roadmap:postmvp:end -->"),
    ("<!-- roadmap:future:start -->", "<!-- roadmap:future:end -->"),
    ("<!-- roadmap:deferred:start -->", "<!-- roadmap:deferred:end -->"),
]

# Section insertion order per file type (canonical positions)
SECTION_ORDER: dict[str, list[str]] = {
    "spec": ["User Scenarios", "Acceptance Criteria", "Functional Requirements", "Edge Cases"],
    "plan": ["Summary", "Implementation Plan", "Testing Strategy", "Risks"],
    "implementation": ["Requirement Mapping", "Acceptance Criteria"],
    "stack": ["Stack", "Rationale"],
    "preflight": ["Tooling", "Authentication", "Tokens"],
}


def _file_created_date(path: Path) -> date:
    """Get file creation date from mtime."""
    ts = path.stat().st_mtime
    return datetime.fromtimestamp(ts).date()


def _title_from_folder(path: Path) -> str:
    """Derive a title from the parent folder name (e.g., 001-user-auth -> User Auth)."""
    folder = path.parent.name
    # Strip leading number prefix
    name = re.sub(r"^\d+-", "", folder)
    return name.replace("-", " ").replace("_", " ").title()


def _inject_section(content: str, section_name: str, file_type: str) -> str:
    """Inject a skeleton section at the canonical position or end of file."""
    skeleton = f"\n\n## {section_name}\n\n*To be completed.*\n"

    order = SECTION_ORDER.get(file_type, [])
    if section_name not in order:
        return content + skeleton

    # Find the position after the last existing section that comes before this one
    target_idx = order.index(section_name)
    lines = content.split("\n")

    # Find the line index of the section that comes just after target in canonical order
    insert_before = None
    for later_section in order[target_idx + 1 :]:
        for i, line in enumerate(lines):
            if line.startswith("## ") and later_section.lower() in line.lower():
                insert_before = i
                break
        if insert_before is not None:
            break

    if insert_before is not None:
        before = "\n".join(lines[:insert_before])
        after = "\n".join(lines[insert_before:])
        return before.rstrip() + skeleton + "\n" + after
    else:
        return content + skeleton


def _inject_roadmap_markers(content: str) -> tuple[str, list[str]]:
    """Inject missing roadmap HTML marker pairs. Returns (new_content, descriptions)."""
    fixes: list[str] = []
    for start_marker, end_marker in ROADMAP_MARKERS:
        if start_marker not in content:
            section = start_marker.split(":")[1]  # e.g., "mvp"
            content += f"\n{start_marker}\n\n{end_marker}\n"
            fixes.append(f"Injected roadmap markers for '{section}'")
    return content, fixes


def fix_file(
    path: Path,
    file_result: FileResult,
    specs_root: Path,
    config: ValidatorConfig,
    dry_run: bool = False,
) -> list[FixAction]:
    """Apply Pass 1 mechanical fixes to a file.

    Args:
        path: Absolute path to the Markdown file.
        file_result: Previous validation result for this file.
        specs_root: Root directory of the .specs/ tree.
        config: Validator configuration.
        dry_run: If True, report fixes without modifying files.

    Returns:
        List of FixAction objects applied. Empty if no errors/warnings or dry_run=True.
    """
    if not file_result.has_errors and not file_result.has_warnings:
        return []

    file_type = resolve_file_type(path, specs_root)
    actions: list[FixAction] = []

    try:
        post = frontmatter.load(str(path))
    except (yaml.YAMLError, OSError) as exc:
        logging.warning("Failed to load %s for fixing: %s", path, exc)
        return []

    metadata = dict(post.metadata)
    content = post.content
    metadata_changed = False
    content_changed = False

    # --- Frontmatter fixes ---

    # Fix empty title
    if (
        file_type in ("spec", "plan", "implementation", "stack")
        and not metadata.get("title", "").strip()
    ):
        metadata["title"] = _title_from_folder(path)
        metadata_changed = True
        actions.append(
            FixAction(path, f"title set to '{metadata['title']}'", "title"),
        )

    if file_type == "spec":
        # Fix invalid status
        if metadata.get("status") not in VALID_STATUSES:
            old = metadata.get("status", "(missing)")
            metadata["status"] = "Draft"
            metadata_changed = True
            actions.append(FixAction(path, f"status '{old}' -> 'Draft'", "status"))

        # Fix invalid priority
        if metadata.get("priority") not in VALID_PRIORITIES:
            old = metadata.get("priority", "(missing)")
            metadata["priority"] = "P2"
            metadata_changed = True
            actions.append(FixAction(path, f"priority '{old}' -> 'P2'", "priority"))

        # Fix missing created
        if "created" not in metadata:
            metadata["created"] = _file_created_date(path)
            metadata_changed = True
            actions.append(FixAction(path, f"created set to {metadata['created']}", "created"))

        # Fix missing updated
        if "updated" not in metadata:
            metadata["updated"] = date.today()
            metadata_changed = True
            actions.append(FixAction(path, f"updated set to {metadata['updated']}", "updated"))

        # Fix updated < created
        created = metadata.get("created")
        updated = metadata.get("updated")
        if isinstance(created, date) and isinstance(updated, date) and updated < created:
            metadata["updated"] = date.today()
            metadata_changed = True
            actions.append(FixAction(path, f"updated corrected to {date.today()}", "updated"))

    if file_type == "plan" and "created" not in metadata:
        metadata["created"] = _file_created_date(path)
        metadata_changed = True
        actions.append(FixAction(path, f"created set to {metadata['created']}", "created"))

    if file_type == "stack" and "updated" not in metadata:
        metadata["updated"] = date.today()
        metadata_changed = True
        actions.append(FixAction(path, f"updated set to {metadata['updated']}", "updated"))

    # --- Section fixes ---

    from .rules.sections import SECTION_RULES, section_present

    rules = SECTION_RULES.get(file_type, {})
    for _key, (keywords, required) in rules.items():
        if required and not section_present(_extract_headings_from_content(content), keywords):
            section_name = keywords[0]
            content = _inject_section(content, section_name, file_type)
            content_changed = True
            actions.append(FixAction(path, f"Injected skeleton section '{section_name}'"))

    # --- Roadmap marker fixes ---

    if file_type == "roadmap":
        content, marker_fixes = _inject_roadmap_markers(content)
        if marker_fixes:
            content_changed = True
            for desc in marker_fixes:
                actions.append(FixAction(path, desc))

    # --- Apply changes ---

    if not actions:
        return []

    if dry_run:
        return actions

    # Backup
    backup_path = path.with_suffix(".md.bak")
    shutil.copy2(path, backup_path)

    # Write
    if metadata_changed:
        post.metadata = metadata
    if content_changed:
        post.content = content

    with open(path, "w", encoding="utf-8") as f:
        f.write(frontmatter.dumps(post))

    # Re-validate
    new_result = validate_file(path, specs_root, config)

    # Check if fix introduced new errors
    old_error_msgs = {e.message for e in file_result.errors}
    new_error_msgs = {e.message for e in new_result.errors}
    new_errors = new_error_msgs - old_error_msgs

    if new_errors:
        # Rollback
        shutil.copy2(backup_path, path)
        backup_path.unlink()
        return [FixAction(path, f"ROLLBACK: fix introduced new errors: {new_errors}")]

    # Remove backup on success
    backup_path.unlink()

    return actions


def _extract_headings_from_content(content: str) -> list[str]:
    """Quick heading extraction from Markdown content (regex-based for speed)."""
    headings = []
    for line in content.splitlines():
        match = re.match(r"^#{2,3}\s+(.+)$", line)
        if match:
            headings.append(match.group(1).strip())
    return headings


def fix_all(
    results: list[FileResult],
    specs_root: Path,
    config: ValidatorConfig,
    dry_run: bool = False,
) -> list[FixAction]:
    """Apply Pass 1 fixes to all files with errors.

    Args:
        results: Validation results from a previous validate_all() run.
        specs_root: Root directory of the .specs/ tree.
        config: Validator configuration.
        dry_run: If True, report fixes without modifying files.

    Returns:
        Combined list of fix actions across all files.
    """
    all_actions: list[FixAction] = []
    for r in results:
        if r.has_errors:
            actions = fix_file(r.path, r, specs_root, config, dry_run)
            all_actions.extend(actions)
    return all_actions
