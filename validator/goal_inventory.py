"""Goal inventory responsibilities behind the public contract facade."""

from __future__ import annotations

import re
from pathlib import Path

from . import goal_contracts as _contracts

__all__ = [
    "_active_execution_task_branches",
    "_detect_any_visual_feature",
    "_detect_penflow",
    "_detect_visual_feature",
    "_detect_visual_feature_slugs",
    "_execution_section_tasks",
    "_extract_definition_of_done",
    "_extract_execution_tasks",
    "_flag_names",
    "_is_all_feature_spec_check",
    "_spec_has_visual_work",
]


def _detect_visual_feature(project_root: Path, feature: str | None) -> bool:
    """Return True if the feature has visual work (## Screens or ## Penflow Contract)."""
    if feature is None:
        return False
    spec_path = project_root / ".specs" / "features" / feature / "spec.md"
    return _contracts._spec_has_visual_work(spec_path)


def _detect_any_visual_feature(project_root: Path) -> bool:
    """Return True if any feature spec declares visual work."""
    return bool(_contracts._detect_visual_feature_slugs(project_root))


def _detect_visual_feature_slugs(project_root: Path) -> list[str]:
    """Return feature slugs whose specs declare visual work."""
    features_dir = project_root / ".specs" / "features"
    if not features_dir.is_dir():
        return []
    return [
        spec_path.parent.name
        for spec_path in sorted(features_dir.glob("*/spec.md"))
        if _contracts._spec_has_visual_work(spec_path)
    ]


def _spec_has_visual_work(spec_path: Path) -> bool:
    """Return True if a feature spec declares visual work headings."""
    if not spec_path.exists():
        return False
    # Explicit `visual: false` opt-out (P0-A marker, see visual_gate) overrides the
    # heading heuristic — CLI-only features documenting a `## Penflow Contract`
    # must not receive receipt-bound visual tasks they can never prove.
    if _contracts.spec_declares_visual_false(spec_path):
        return False
    return bool(_contracts.VISUAL_FEATURE_HEADING_RE.search(spec_path.read_text(encoding="utf-8")))


def _detect_penflow(project_root: Path) -> bool:
    """Return True if a penflow/ directory exists at the project root."""
    return (project_root / "penflow").is_dir()


def _flag_names(normalized_flags: list[str]) -> set[str]:
    """Return flag names without values from normalized command tokens."""
    return {token.split("=", 1)[0] for token in normalized_flags if token.startswith("-")}


def _is_all_feature_spec_check(
    *,
    command: str,
    feature: str | None,
    normalized_flags: list[str],
) -> bool:
    """Return True when spec-check is compiling an all-feature goal."""
    return (
        command == "spec-check"
        and feature is None
        and bool(
            _contracts._flag_names(normalized_flags).intersection(
                _contracts.SPEC_CHECK_ALL_FEATURE_FLAGS
            )
        )
    )


def _active_execution_task_branches(
    *,
    normalized_flags: list[str],
    is_visual: bool,
    visual_enabled: bool,
    has_penflow: bool,
    audit_only: bool,
    no_generate: bool,
    command: str | None = None,
) -> set[str]:
    """Calculate which execution task branches are active based on context."""
    active: set[str] = {"always"}
    flag_names = _contracts._flag_names(normalized_flags)
    # @spec(FR-015): preparation exits before implementation checks or mutation.
    if "--pre-impl" in flag_names:
        active.add("pre-impl")
        if is_visual and has_penflow:
            active.add("pre-impl-penflow")
        return active
    active.add("full-check")
    generate_active, execute_active = _execution_modes(flag_names, audit_only, no_generate, command)
    active |= _command_task_branches(command, flag_names, execute_active)
    visual_active = (
        is_visual
        and visual_enabled
        and (execute_active or command not in {"spec-test", "spec-fix"})
    )
    if flag_names.intersection({"--surfaces"}):
        active.add("surfaces")
    if flag_names.intersection({"--quality", "-q"}):
        active.add("quality-only")
    if flag_names.intersection({"--tree-only", "-t"}):
        active.add("tree-only")
    if flag_names.intersection({"--visual-status"}):
        active.add("visual-status")
    if flag_names.intersection({"--all", "-A", "--summary", "-S"}):
        active.add("multi")
    if flag_names.intersection({"--fix", "-x"}):
        active.add("fix")
    if visual_active:
        active.add("visual")
        if has_penflow:
            active.add("penflow")
    if generate_active:
        active.add("generate")
    if generate_active and is_visual and visual_enabled:
        active.add("visual-generate")
    if execute_active:
        active.add("execute")
    return active


def _execution_modes(
    flag_names: set[str], audit_only: bool, no_generate: bool, command: str | None
) -> tuple[bool, bool]:
    """Return generation/execution applicability for existing preview and regeneration modes."""
    if command == "spec-fix":
        enabled = "fix-execute" in _fix_execution_branches(flag_names)
        return enabled and not no_generate, enabled
    if command != "spec-test":
        return not audit_only and not no_generate, not audit_only
    if audit_only or flag_names.intersection({"--audit-only", "-a", "--dry-run"}):
        return False, False
    can_generate = not no_generate and not flag_names.intersection({"--no-generate", "-G"})
    # Regeneration confirmation permits writes only; its documented flow skips execution.
    if "--regenerate-missing" in flag_names:
        return bool(can_generate and "--confirm" in flag_names), False
    return bool(can_generate), True


def _fix_execution_branches(flag_names: set[str]) -> set[str]:
    """Scope fix proof to feature execution, excluding previews, debt and batch wrappers."""
    if flag_names.intersection({"--dry-run", "-d", "--audit-only", "--conventions", "--all", "-A"}):
        if "--conventions" in flag_names and not flag_names.intersection(
            {"--dry-run", "-d", "--audit-only", "--all", "-A"}
        ):
            return {"fix-conventions"}
        return set()
    active = {"fix-execute"}
    # A filtered repair certifies its mapped assertions, not unrelated feature ACs.
    if not flag_names.intersection(
        {"--fr", "--ac", "--visual", "-v", "--functional", "-f", "--no-visual", "-V"}
    ):
        active.add("fix-feature")
    return active


def _command_task_branches(command: str | None, flags: set[str], executes: bool) -> set[str]:
    """Retain audit reporting while excluding preview and generation-only publication."""
    if command == "spec-fix":
        return _fix_execution_branches(flags)
    if command != "spec-test":
        return set()
    active = (
        {"test-report"} if not flags.intersection({"--dry-run", "--regenerate-missing"}) else set()
    )
    if executes and "--visual" not in flags:
        active.add("test-suite")
    return active


# Parse ## Execution Tasks from the skill file and filter by active branches.
#
# Branches:
# always          — always included
# visual          — is_visual AND NOT --no-visual
# penflow         — visual AND has_penflow
# generate        — NOT --audit-only AND NOT --no-generate
# visual-generate — visual AND generate both active
# execute         — NOT --audit-only
# surfaces        — --surfaces
# quality-only    — --quality or -q
# tree-only       — --tree-only or -t
# visual-status   — --visual-status
# multi           — --all/-A or --summary/-S
# fix             — --fix or -x
# pre-impl        — --pre-impl
# full-check      — NOT --pre-impl
# pre-impl-penflow — --pre-impl AND visual AND has_penflow (inspection only)
#
def _extract_execution_tasks(
    skill_path: Path,
    *,
    normalized_flags: list[str],
    is_visual: bool,
    has_penflow: bool,
) -> list[str]:
    """Read task inventory and apply the documented execution branches."""
    if not skill_path.exists():
        return []
    text = skill_path.read_text(encoding="utf-8")
    # Find the machine-readable execution task section heading
    match = re.search(r"^##\s+Execution Tasks\s*$", text, flags=re.MULTILINE)
    if match is None:
        return []
    section = text[match.end() :]
    next_heading = re.search(r"^##\s+", section, flags=re.MULTILINE)
    if next_heading is not None:
        section = section[: next_heading.start()]

    no_visual = "--no-visual" in normalized_flags
    audit_only = "--audit-only" in normalized_flags
    no_generate = "--no-generate" in normalized_flags

    active = _contracts._active_execution_task_branches(
        normalized_flags=normalized_flags,
        command=skill_path.parent.name,
        is_visual=is_visual,
        visual_enabled=not no_visual,
        has_penflow=has_penflow,
        audit_only=audit_only,
        no_generate=no_generate,
    )

    return _contracts._execution_section_tasks(section, active, skill_path)


def _execution_section_tasks(section: str, active: set[str], skill_path: Path) -> list[str]:
    tasks: list[str] = []
    for line in section.splitlines():
        stripped = line.strip()
        # Parse - [branch] task description format
        m = re.match(r"^-\s+\[([^\]]+)\]\s+(.+)$", stripped)
        if m is None:
            continue
        branch = m.group(1).strip()
        if branch in {"", " ", "x", "X"}:
            continue
        if branch not in _contracts.EXECUTION_TASK_BRANCHES:
            raise ValueError(f"Unknown execution task branch '{branch}' in {skill_path}")
        task = m.group(2).strip()
        if branch in active:
            tasks.append(_contracts.strip_evidence_marker(task))
    return tasks


def _extract_definition_of_done(
    skill_path: Path, *, active_branches: set[str] | None = None
) -> list[str]:
    """Read legacy unconditional checkboxes and explicitly branch-scoped criteria."""
    if not skill_path.exists():
        return []
    text = skill_path.read_text(encoding="utf-8")
    match = re.search(
        r"^##\s+Definition of Done \(Command-Level\)\s*$",
        text,
        flags=re.MULTILINE,
    )
    if match is None:
        return []
    section = text[match.end() :]
    next_heading = re.search(r"^##\s+", section, flags=re.MULTILINE)
    if next_heading is not None:
        section = section[: next_heading.start()]
    items: list[str] = []
    for line in section.splitlines():
        stripped = line.strip()
        if not stripped.startswith("- [ ]"):
            continue
        item = stripped.removeprefix("- [ ]").strip()
        branch_match = re.match(r"^\[([^\]]+)\]\s+(.+)$", item)
        if branch_match is not None:
            branch, item = branch_match.groups()
            if branch not in _contracts.EXECUTION_TASK_BRANCHES:
                raise ValueError(f"Unknown Definition of Done branch '{branch}' in {skill_path}")
            if active_branches is not None and branch not in active_branches:
                continue
        if item:
            items.append(item)
    return items
