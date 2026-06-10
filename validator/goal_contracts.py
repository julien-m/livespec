# LiveSpec traceability anchors
# @spec(FR-001)
# @spec(FR-002)
# @spec(FR-003)
# @spec(FR-004)
# @spec(FR-005)
# @spec(FR-006)
# @spec(FR-007)
# @spec(FR-009)
# @spec(FR-010)
# @spec(FR-012)
# @spec(FR-013)
# @spec(FR-014)
# @spec(FR-015)
# @spec(FR-016)
# @spec(FR-017)
# @spec(FR-018)
# @spec(FR-019)

"""Deterministic command goal contract compiler.

# @spec FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-007, FR-010, FR-012, FR-013, FR-019
#   — .specs/features/052-deterministic-command-goal-contracts/spec.md
"""

from __future__ import annotations

import hashlib
import json
import re
import shlex
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypeAlias, cast

from .command_registry import normalize_command_name
from .exceptions import ExpectationsInvalid
from .expectations import ExpectationsFile, Rule, load_expectations
from .finalize import FinalizeReceiptError, verify_finalize_receipt
from .visual_evidence import VisualReceiptError, verify_visual_receipt

GOAL_CONTRACT_VERSION = "2.0"
RequiredConventions: TypeAlias = dict[str, str | list[str]]
CONVENTION_SIGNAL_FILES: tuple[str, ...] = ("spec.md", "plan.md")
EXECUTION_TASK_BRANCHES: frozenset[str] = frozenset(
    {
        "always",
        "visual",
        "penflow",
        "generate",
        "visual-generate",
        "execute",
        "surfaces",
        "quality-only",
        "tree-only",
        "visual-status",
        "multi",
        "fix",
    }
)
ALLOWED_INTERNAL_INVOCATION_MODES: frozenset[str] = frozenset({"subagent", "suggestion"})
INTERNAL_SUBAGENT_GUARD_REQUIREMENTS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("project_root", ("project_root",)),
    ("cwd/working directory", ("cwd", "working directory", "workdir")),
    (".specs/spec-system.md", (".specs/spec-system.md",)),
)
MARKDOWN_HORIZONTAL_RULES: frozenset[str] = frozenset({"---", "***", "___"})
DESIGN_SIGNAL_WORDS: frozenset[str] = frozenset(
    {
        "--visual",
        "baseline",
        "css",
        "design",
        "mockup",
        "penflow",
        "screen",
        "theme.css",
        "ui",
        "visual",
    }
)
SPEC_CHECK_ALL_FEATURE_FLAGS: frozenset[str] = frozenset({"--all", "-A"})
GENERIC_REQUIRED_EVIDENCE: tuple[str, ...] = (
    "observable_output_or_artifact",
    "success_criteria_met",
)
GENERIC_REPAIR_ACTIONS: tuple[str, ...] = (
    "Run the described task and capture concrete evidence before proving it.",
    "If the task cannot run, emit a canonical BLOCKED line with the exact reason.",
)
VISUAL_DESIGN_REQUIRED_EVIDENCE: tuple[str, ...] = ("visual_evidence_receipt_path",)
VISUAL_DESIGN_INVALID_SUBSTITUTES: tuple[str, ...] = (
    "normalized_json_alignment_only",
    "penflow_tree_match_without_png_comparison",
    "global_visual_gate_pass_without_png_paths",
    "design_alignment_report_as_pixel_report",
    "worker_declared_diff_without_receipt",
)
VISUAL_DESIGN_REPAIR_ACTIONS: tuple[str, ...] = (
    "export mockup PNGs from the design source "
    "(for example penflow/ui.pen) into .specs/design/screens/",
    "create or refresh valid baseline/runtime PNGs for the same screen set",
    "run `livespec visual-gate certify --feature <slug> --command <command> "
    "--target <target> --run-id <run-id> --json` and submit the generated receipt.json path",
)
# @spec FR-005: finalize.registry evidence family constants
#   — .specs/features/058-deterministic-finalization/spec.md#fr-005
FINALIZE_REQUIRED_EVIDENCE: tuple[str, ...] = ("finalize_receipt_path",)
FINALIZE_INVALID_SUBSTITUTES: tuple[str, ...] = (
    "prose_finalization_claim",
    "exit_code_without_receipt",
    "declared_file_list_without_receipt",
)
FINALIZE_REPAIR_ACTIONS: tuple[str, ...] = (
    "run `livespec finalize apply --feature <slug> --command <command> --entry-file <entry.md>`",
    "run `livespec finalize verify --feature <slug> --command <command>` and "
    "submit the generated receipt.json path",
)

# Match level-2 headings that declare visual/Penflow feature work.
VISUAL_FEATURE_HEADING_RE = re.compile(
    r"^##\s+(Screens|Penflow Contract)\b",
    re.MULTILINE,
)
CHILD_GOAL_ARTIFACT_ROOT_MARKER = "livespec-goals"


@dataclass(frozen=True)
class GoalContract:
    """Canonical command goal compiled from versioned command contracts."""

    command: str
    payload: dict[str, Any]
    canonical_json: str
    goal_hash: str
    objective: str

    def to_json_envelope(self) -> dict[str, Any]:
        """Return the CLI JSON envelope."""
        return {
            "command": self.command,
            "hash": self.goal_hash,
            "canonical": self.payload,
            "canonical_json": self.canonical_json,
            "objective": self.objective,
        }


def normalize_goal_flags(flags: str | list[str] | tuple[str, ...] | None) -> list[str]:
    """Normalize active command flags into stable, order-independent tokens.

    Args:
        flags: Space-delimited flags or a pre-tokenized flag list.

    Returns:
        Sorted unique tokens, with ``--flag value`` normalized to ``--flag=value``.
    """
    if flags is None:
        tokens: list[str] = []
    elif isinstance(flags, str):
        tokens = shlex.split(flags)
    else:
        tokens = list(flags)

    normalized: list[str] = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if not token.startswith("-"):
            index += 1
            continue
        if "=" in token:
            normalized.append(token)
            index += 1
            continue
        next_index = index + 1
        if next_index < len(tokens) and not tokens[next_index].startswith("-"):
            normalized.append(f"{token}={tokens[next_index]}")
            index += 2
            continue
        normalized.append(token)
        index += 1
    return sorted(set(normalized))


def compile_command_goal(
    command: str,
    *,
    project_root: Path,
    livespec_root: Path,
    feature: str | None = None,
    flags: str | list[str] | tuple[str, ...] | None = None,
) -> GoalContract:
    """Compile a deterministic goal contract for a LiveSpec command.

    Args:
        command: Command name or alias.
        project_root: Project root containing ``.specs``.
        livespec_root: LiveSpec checkout root.
        feature: Resolved feature slug, if the command is feature-scoped.
        flags: Active command flags.

    Returns:
        Deterministic :class:`GoalContract`.
    """
    normalized_command = normalize_command_name(command)
    expectations = load_expectations(
        normalized_command,
        project_root,
        livespec_root,
    )
    payload = _goal_payload(
        command=normalized_command,
        expectations=expectations,
        livespec_root=livespec_root,
        project_root=project_root,
        feature=feature,
        flags=flags,
    )
    canonical_json = _canonical_json(payload)
    goal_hash = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
    contract = GoalContract(
        command=normalized_command,
        payload=payload,
        canonical_json=canonical_json,
        goal_hash=goal_hash,
        objective="",
    )
    objective = render_goal_objective(contract)
    return GoalContract(
        command=normalized_command,
        payload=payload,
        canonical_json=canonical_json,
        goal_hash=goal_hash,
        objective=objective,
    )


def _detect_visual_feature(project_root: Path, feature: str | None) -> bool:
    """Return True if the feature has visual work (## Screens or ## Penflow Contract)."""
    if feature is None:
        return False
    spec_path = project_root / ".specs" / "features" / feature / "spec.md"
    return _spec_has_visual_work(spec_path)


def _detect_any_visual_feature(project_root: Path) -> bool:
    """Return True if any feature spec declares visual work."""
    return bool(_detect_visual_feature_slugs(project_root))


def _detect_visual_feature_slugs(project_root: Path) -> list[str]:
    """Return feature slugs whose specs declare visual work."""
    features_dir = project_root / ".specs" / "features"
    if not features_dir.is_dir():
        return []
    return [
        spec_path.parent.name
        for spec_path in sorted(features_dir.glob("*/spec.md"))
        if _spec_has_visual_work(spec_path)
    ]


def _spec_has_visual_work(spec_path: Path) -> bool:
    """Return True if a feature spec declares visual work headings."""
    if not spec_path.exists():
        return False
    return bool(VISUAL_FEATURE_HEADING_RE.search(spec_path.read_text(encoding="utf-8")))


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
        and bool(_flag_names(normalized_flags).intersection(SPEC_CHECK_ALL_FEATURE_FLAGS))
    )


def _active_execution_task_branches(
    *,
    normalized_flags: list[str],
    is_visual: bool,
    visual_enabled: bool,
    has_penflow: bool,
    audit_only: bool,
    no_generate: bool,
) -> set[str]:
    """Calculate which execution task branches are active based on context."""
    active: set[str] = {"always"}
    flag_names = _flag_names(normalized_flags)
    visual_active = is_visual and visual_enabled
    generate_active = not audit_only and not no_generate
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
            active.add("visual-generate")
    if generate_active:
        active.add("generate")
    if not audit_only:
        active.add("execute")
    return active


def _extract_execution_tasks(
    skill_path: Path,
    *,
    normalized_flags: list[str],
    is_visual: bool,
    has_penflow: bool,
) -> list[str]:
    """Parse ## Execution Tasks from the skill file and filter by active branches.

    Branches:
      always          — always included
      visual          — is_visual AND NOT --no-visual
      penflow         — visual AND has_penflow
      generate        — NOT --audit-only AND NOT --no-generate
      visual-generate — visual AND generate both active
      execute         — NOT --audit-only
      surfaces        — --surfaces
      quality-only    — --quality or -q
      tree-only       — --tree-only or -t
      visual-status   — --visual-status
      multi           — --all/-A or --summary/-S
      fix             — --fix or -x
    """
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

    active = _active_execution_task_branches(
        normalized_flags=normalized_flags,
        is_visual=is_visual,
        visual_enabled=not no_visual,
        has_penflow=has_penflow,
        audit_only=audit_only,
        no_generate=no_generate,
    )

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
        if branch not in EXECUTION_TASK_BRANCHES:
            raise ValueError(f"Unknown execution task branch '{branch}' in {skill_path}")
        task = m.group(2).strip()
        if branch in active:
            tasks.append(task)
    return tasks


def _extract_internal_command_invocations(skill_path: Path) -> list[dict[str, str]]:
    """Parse and validate executable internal slash-command invocations.

    The ``## Internal Command Invocations`` section is the machine-readable
    allowlist for nested slash calls. Executed ``/spec-*`` calls must run in an
    independent native sub-agent so each sub-command can set and complete its
    own goal. Text-only next-step hints use ``suggestion`` mode.
    """
    if not skill_path.exists():
        return []
    text = skill_path.read_text(encoding="utf-8")
    # Locate the machine-readable invocation section by its level-2 heading.
    match = re.search(
        r"^##\s+Internal Command Invocations\s*$",
        text,
        flags=re.MULTILINE,
    )
    if match is None:
        _reject_undocumented_internal_spec_invocation(skill_path, text)
        return []
    section = text[match.end() :]
    next_heading = re.search(r"^##\s+", section, flags=re.MULTILINE)
    if next_heading is not None:
        section = section[: next_heading.start()]

    invocations: list[dict[str, str]] = []
    for line_number, line in enumerate(section.splitlines(), 1):
        parsed = _parse_internal_invocation_line(
            line,
            skill_path=skill_path,
            line_number=line_number,
        )
        if parsed is None:
            continue
        if parsed["mode"] not in ALLOWED_INTERNAL_INVOCATION_MODES:
            raise ExpectationsInvalid(
                skill_path.as_posix(),
                "Internal Command Invocations rows must use mode subagent or suggestion "
                f"at Internal Command Invocations line {line_number}: "
                f"{parsed['mode']}",
            )
        if parsed["mode"] == "subagent" and not parsed["command"].startswith("/spec-"):
            raise ExpectationsInvalid(
                skill_path.as_posix(),
                "Internal Command Invocations subagent rows must execute /spec-* "
                f"commands at line {line_number}: {parsed['command']}",
            )
        if parsed["mode"] == "subagent":
            _validate_internal_subagent_context_guard(
                parsed,
                skill_path=skill_path,
                line_number=line_number,
            )
        invocations.append(parsed)
    return invocations


def validate_internal_command_invocation_guards(skill_path: Path) -> None:
    """Validate nested slash-command rows for audit callers."""
    _extract_internal_command_invocations(skill_path)


def _validate_internal_subagent_context_guard(
    invocation: dict[str, str],
    *,
    skill_path: Path,
    line_number: int,
) -> None:
    """Require project-root propagation on native nested slash-command rows."""
    haystack = " ".join((invocation["command"], invocation["purpose"])).lower()
    missing = [
        label
        for label, accepted_terms in INTERNAL_SUBAGENT_GUARD_REQUIREMENTS
        if not any(term in haystack for term in accepted_terms)
    ]
    if not missing:
        return
    raise ExpectationsInvalid(
        skill_path.as_posix(),
        "Internal Command Invocations subagent rows must mention project_root, "
        "cwd/working directory, and .specs/spec-system.md "
        f"at line {line_number}; missing: {', '.join(missing)}",
    )


def _reject_undocumented_internal_spec_invocation(
    skill_path: Path,
    text: str,
) -> None:
    """Reject executable nested slash commands without an allowlist section."""
    current_command = skill_path.parent.name
    in_fence = False
    for line_number, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        lowered = line.lower()
        if "/spec-" not in lowered:
            continue
        if not any(verb in lowered for verb in ("run", "execute", "spawn")):
            continue
        if not _looks_like_executable_internal_invocation(stripped):
            continue
        commands = set(re.findall(r"/(spec-[a-z0-9-]+)", lowered))
        if commands and commands <= {current_command}:
            continue
        if _is_documentary_internal_invocation_reference(stripped):
            continue
        raise ExpectationsInvalid(
            skill_path.as_posix(),
            "Executable internal /spec-* invocation requires "
            "## Internal Command Invocations "
            f"at line {line_number}: {line.strip()}",
        )


def _looks_like_executable_internal_invocation(line: str) -> bool:
    """Return True when a line directs the agent to execute a slash command."""
    normalized = re.sub(r"^[-*]\s+", "", line.strip())
    normalized = re.sub(r"^\d+\.\s+", "", normalized)
    lowered = normalized.lower()
    if lowered.startswith(("run ", "run `", "execute ", "execute `", "spawn ", "spawn `")):
        return True
    return any(
        marker in lowered
        for marker in (
            " must run ",
            " must execute ",
            " must spawn ",
            " then run ",
            " then execute ",
            " then spawn ",
        )
    )


def _is_documentary_internal_invocation_reference(line: str) -> bool:
    """Return True for examples, recovery hints, and display text, not execution."""
    lowered = line.lower()
    if line.startswith("|") or lowered.startswith((">", "#", "**")):
        return True
    documentary_markers = (
        "suggest",
        "recovery",
        "recover",
        "re-run",
        "rerun",
        "blocked",
        "error",
        "message",
        "output",
        "example",
        "usage",
        "typically run",
        "can run",
        "if `.specs/` does not exist",
        "if .specs/ does not exist",
        "does not exist",
        "not initialized",
        "on blocked",
        "resume with",
        "next useful action",
        "legacy alias",
        "aliases such as",
    )
    return any(marker in lowered for marker in documentary_markers)


def _parse_internal_invocation_line(
    line: str,
    *,
    skill_path: Path,
    line_number: int,
) -> dict[str, str] | None:
    """Parse ``- [mode] `command` — purpose`` invocation rows."""
    stripped = line.strip()
    if stripped in MARKDOWN_HORIZONTAL_RULES:
        return None
    if not stripped or not stripped.startswith("-"):
        return None
    # Parse "- [mode] `command` — purpose" rows from the invocation allowlist.
    match = re.match(r"^-\s+\[([^\]]+)\]\s+`([^`]+)`(?:\s+[—-]\s+(.+))?$", stripped)
    if match is None:
        raise ExpectationsInvalid(
            skill_path.as_posix(),
            f"Malformed Internal Command Invocations bullet row at line {line_number}: {stripped}",
        )
    mode = match.group(1).strip()
    command = match.group(2).strip()
    purpose = (match.group(3) or "").strip()
    return {
        "mode": mode,
        "command": command,
        "purpose": purpose,
    }


def render_goal_contract_file(goal: GoalContract) -> str:
    """Render the immutable JSON contract consumed by ``livespec goal prove``.

    Args:
        goal: Compiled deterministic goal contract.

    Returns:
        Pretty-printed JSON contract text. The function has no filesystem
        side effects; callers decide where to persist it.
    """
    contract = {
        "schema_version": GOAL_CONTRACT_VERSION,
        "goal_hash": goal.goal_hash,
        "command": goal.command,
        "feature": goal.payload.get("feature"),
        "normalized_flags": list(goal.payload.get("normalized_flags") or []),
        "mode": goal.payload["mode"],
        "worker_may_mark_tasks_complete": False,
        "rules": goal.payload["rules"],
        "tasks": goal.payload["tasks"],
        "definition_of_done": goal.payload["definition_of_done"],
        "runtime_context": goal.payload["runtime_context"],
        "canonical": goal.payload,
        "canonical_json": goal.canonical_json,
    }
    return json.dumps(contract, indent=2, sort_keys=True, ensure_ascii=False)


def render_goal_state_file(goal: GoalContract) -> str:
    """Render the mutable JSON state file; only ``goal prove`` updates it.

    Args:
        goal: Compiled deterministic goal contract.

    Returns:
        Pretty-printed JSON state initialized with every task pending. The
        function has no filesystem side effects; callers persist the text.
    """
    state: dict[str, Any] = {
        "schema_version": GOAL_CONTRACT_VERSION,
        "goal_hash": goal.goal_hash,
        "command": goal.command,
        "status": "active",
        "tasks": {
            task["id"]: {
                "ordinal": task["ordinal"],
                "description": task["description"],
                "status": "pending",
                "attempts": [],
                "accepted_evidence": None,
                "last_rejection": None,
            }
            for task in goal.payload["tasks"]
        },
    }
    return json.dumps(state, indent=2, sort_keys=True, ensure_ascii=False)


def render_goal_status(state: dict[str, Any]) -> str:
    """Render a compact status summary for a goal state JSON object.

    Args:
        state: Mutable goal state JSON object.

    Returns:
        One-line status summary with goal hash, status, completed count, and
        pending count.
    """
    tasks = dict(state.get("tasks") or {})
    total = len(tasks)
    complete = sum(1 for task in tasks.values() if task.get("status") == "complete")
    pending = total - complete
    status = state.get("status") or "unknown"
    return (
        f"goal_hash:{state.get('goal_hash', 'unknown')} | "
        f"status:{status} | complete:{complete}/{total} | pending:{pending}"
    )


def prove_goal_task(
    contract: dict[str, Any],
    state: dict[str, Any],
    task_id: str,
    evidence: dict[str, Any],
    *,
    project_root: Path | None = None,
) -> dict[str, Any]:
    """Validate evidence for one contract task and return an updated state.

    Workers submit evidence; this function is the sole actor that marks a task
    complete. Missing proof returns ``REJECTED_NEEDS_ACTION`` and leaves the task
    pending so the executor must repair and resubmit.
    """
    tasks: dict[str, dict[str, Any]] = {}
    contract_tasks: object = contract.get("tasks")
    if isinstance(contract_tasks, list):
        for task_item in cast(list[object], contract_tasks):
            if not isinstance(task_item, dict):
                continue
            task_dict = cast(dict[str, Any], task_item)
            task_id_value = task_dict.get("id")
            if isinstance(task_id_value, str):
                tasks[task_id_value] = task_dict
    task = tasks.get(task_id)
    updated_state = cast(dict[str, Any], json.loads(json.dumps(state)))
    if task is None:
        return {
            "task_id": task_id,
            "status": "REJECTED_UNKNOWN_TASK",
            "accepted": False,
            "missing_evidence": ["known_task_id"],
            "invalid_substitutes": [],
            "required_actions": ["Use a task id listed in contract.tasks."],
            "state": updated_state,
        }

    task_state = _ensure_state_task(updated_state, task)
    proof = _validate_task_evidence(
        task,
        evidence,
        contract=contract,
        project_root=project_root,
    )
    attempt = {
        "status": proof["status"],
        "evidence": evidence,
        "missing_evidence": proof["missing_evidence"],
        "invalid_substitutes": proof["invalid_substitutes"],
    }
    task_state.setdefault("attempts", []).append(attempt)
    if proof["accepted"]:
        task_state["status"] = "complete"
        task_state["accepted_evidence"] = evidence
        task_state["last_rejection"] = None
    else:
        task_state["status"] = "pending"
        task_state["last_rejection"] = {
            "missing_evidence": proof["missing_evidence"],
            "invalid_substitutes": proof["invalid_substitutes"],
            "required_actions": proof["required_actions"],
        }
    _refresh_state_status(updated_state)
    return {
        "task_id": task_id,
        "status": proof["status"],
        "accepted": proof["accepted"],
        "missing_evidence": proof["missing_evidence"],
        "invalid_substitutes": proof["invalid_substitutes"],
        "required_actions": proof["required_actions"],
        "state": updated_state,
    }


def render_goal_objective(goal: GoalContract) -> str:
    """Render stable human text from the canonical payload."""
    payload = goal.payload
    lines = [
        f"Goal hash: {goal.goal_hash}",
        f"Command: {payload['command']}",
        f"Feature: {payload['feature'] or 'none'}",
        f"Flags: {', '.join(payload['normalized_flags']) or 'none'}",
    ]
    execution_tasks = list(payload.get("execution_tasks") or [])
    if execution_tasks:
        lines.append("")
        lines.append("Execution tasks (in order):")
        for i, task in enumerate(execution_tasks, 1):
            lines.append(f"  {i:>2}. {task}")
    tasks = list(payload.get("tasks") or [])
    # @spec FR-005: Render task-level convention replay
    #   — .specs/features/053-goal-tasks-replay-required-conventions-per-step/spec.md#fr-005
    convention_tasks = [
        task for task in tasks if isinstance(task, dict) and task.get("required_conventions")
    ]
    if convention_tasks:
        lines.append("")
        lines.append("Task-level convention replay:")
        for task in convention_tasks:
            required = cast(dict[str, Any], task["required_conventions"])
            domains = ", ".join(cast(list[str], required.get("domains") or []))
            sources = ", ".join(cast(list[str], required.get("source_paths") or []))
            lines.append(f"- {task['id']}: read_apply domains [{domains}] from {sources}")
    lines.append("")
    lines.append("Definition of Done:")
    definition_of_done = list(payload["definition_of_done"])
    if definition_of_done:
        lines.extend(f"- {item}" for item in definition_of_done)
    else:
        lines.append("- No Definition of Done found in command skill; use expectations only.")
    conventions = payload.get("conventions", {})
    selected_domains = list(conventions.get("selected_domains") or [])
    if selected_domains:
        lines.append("")
        lines.append("Conventions to apply:")
        for domain in selected_domains:
            lines.append(f"- {domain['name']}: {', '.join(domain['paths'])}")
    sections = payload["expectation_sections"]
    for label, key in (
        ("Preconditions", "preconditions"),
        ("Filesystem effects", "filesystem_effects"),
        ("Produced artifacts", "produced_artifacts"),
        ("Post-run checks", "post_run_checks"),
    ):
        values = list(sections[key])
        if not values:
            continue
        lines.append("")
        lines.append(f"{label}:")
        lines.extend(f"- {value}" for value in values)
    lines.append("")
    lines.append("Verification rules:")
    for rule in payload["verify_rules"]["must"]:
        lines.append(f"- must {rule['kind']}: {rule['payload']}")
    for rule in payload["verify_rules"]["must_not"]:
        lines.append(f"- must_not {rule['kind']}: {rule['payload']}")
    return "\n".join(lines)


def _goal_payload(
    *,
    command: str,
    expectations: ExpectationsFile,
    livespec_root: Path,
    project_root: Path,
    feature: str | None,
    flags: str | list[str] | tuple[str, ...] | None,
) -> dict[str, Any]:
    skill_path = livespec_root / ".agent-sync" / "skills" / command / "SKILL.md"
    normalized_flags = normalize_goal_flags(flags)
    is_visual = _detect_visual_feature(project_root, feature)
    if not is_visual and _is_all_feature_spec_check(
        command=command,
        feature=feature,
        normalized_flags=normalized_flags,
    ):
        is_visual = _detect_any_visual_feature(project_root)
    visual_feature_slugs = [feature] if feature and is_visual else []
    if not visual_feature_slugs and _is_all_feature_spec_check(
        command=command,
        feature=feature,
        normalized_flags=normalized_flags,
    ):
        visual_feature_slugs = _detect_visual_feature_slugs(project_root)
    has_penflow = _detect_penflow(project_root)
    execution_tasks = _extract_execution_tasks(
        skill_path,
        normalized_flags=normalized_flags,
        is_visual=is_visual,
        has_penflow=has_penflow,
    )
    definition_of_done = _extract_definition_of_done(skill_path)
    conventions = _compile_conventions_payload(
        command=command,
        expectations=expectations,
        project_root=project_root,
        feature=feature,
        normalized_flags=normalized_flags,
    )
    tasks = _build_goal_tasks(
        command=command,
        execution_tasks=execution_tasks,
        definition_of_done=definition_of_done,
        visual_feature_slugs=visual_feature_slugs,
        conventions=conventions,
    )
    payload = {
        "schema_version": GOAL_CONTRACT_VERSION,
        "command": command,
        "feature": feature,
        "normalized_flags": normalized_flags,
        "mode": "enforced",
        "rules": {
            "completion_actor": "goal",
            "proof_required_for_each_task": True,
            "worker_may_mark_tasks_complete": False,
            "missing_evidence_status": "REJECTED_NEEDS_ACTION",
            "blocked_requires_canonical_line": True,
        },
        "runtime_context": {
            "is_visual_feature": is_visual,
            "has_penflow": has_penflow,
            "visual_feature_slugs": visual_feature_slugs,
        },
        "execution_tasks": execution_tasks,
        "tasks": tasks,
        "internal_command_invocations": _extract_internal_command_invocations(skill_path),
        "expectations": {
            "command": expectations.command,
            "contract_version": expectations.contract_version,
            "last_reviewed": expectations.last_reviewed,
            "source_path": _stable_path(
                expectations.source_path,
                project_root=project_root,
                livespec_root=livespec_root,
            ),
        },
        "conventions": conventions,
        "expectation_sections": {
            "purpose": _normalize_section_lines(expectations.prose_sections["1. Purpose"]),
            "preconditions": _normalize_section_lines(
                expectations.prose_sections["2. Preconditions"]
            ),
            "filesystem_effects": _normalize_section_lines(
                expectations.prose_sections["4. Filesystem Effects"]
            ),
            "produced_artifacts": _normalize_section_lines(
                expectations.prose_sections["6. Produced Artifacts"]
            ),
            "post_run_checks": _normalize_section_lines(
                expectations.prose_sections["10. Post-run Checks"]
            ),
        },
        "definition_of_done": definition_of_done,
        "verify_rules": {
            "must": _canonical_rules(expectations.verify.must),
            "may": _canonical_rules(expectations.verify.may),
            "must_not": _canonical_rules(expectations.verify.must_not),
            "when": [
                {
                    "flag": branch.flag,
                    "must": _canonical_rules(branch.must),
                    "may": _canonical_rules(branch.may),
                    "must_not": _canonical_rules(branch.must_not),
                }
                for branch in expectations.verify.when
            ],
        },
    }
    return payload


def _build_goal_tasks(
    *,
    command: str,
    execution_tasks: list[str],
    definition_of_done: list[str],
    visual_feature_slugs: list[str],
    conventions: Mapping[str, object],
) -> list[dict[str, Any]]:
    """Convert command task prose into enforced proof tasks."""
    # Build base proof tasks first, then layer optional convention evidence onto
    # every task when conventions were selected.
    rows: list[tuple[str, str]] = [("execution", task) for task in execution_tasks]
    rows.extend(("definition_of_done", item) for item in definition_of_done)
    if not rows:
        rows.append(("execution", "Follow command SKILL.md phases and expectations."))

    tasks: list[dict[str, Any]] = []
    seen: set[str] = set()
    required_conventions = _task_required_conventions(conventions)
    required_convention_domains: list[str] = []
    required_convention_sources: list[str] = []
    if required_conventions is not None:
        required_convention_domains = cast(list[str], required_conventions["domains"])
        required_convention_sources = cast(list[str], required_conventions["source_paths"])
    for ordinal, (category, description) in enumerate(rows, 1):
        task_id = _unique_task_id(
            _task_id_for_description(command, category, ordinal, description),
            seen,
            ordinal,
        )
        feature_targets: list[str | None] = [None]
        if task_id in {"visual.design_fidelity", "visual.pixel_regression"}:
            feature_targets = list(visual_feature_slugs) or [None]
        for feature_slug in feature_targets:
            effective_id = task_id
            effective_description = description
            if feature_slug is not None:
                effective_description = f"{description} [feature: {feature_slug}]"
            if feature_slug is not None and len(feature_targets) > 1:
                effective_id = _unique_task_id(
                    f"{task_id}.{_slugify_task_id(feature_slug)}",
                    seen,
                    ordinal,
                )
            required_evidence = list(_required_evidence_for_task(task_id, description))
            repair_actions = list(_repair_actions_for_task(task_id, description))
            if required_conventions is not None:
                # @spec FR-002: Convention proof fields, FR-004: Convention repair actions
                #   — .specs/features/053-goal-tasks-replay-required-conventions-per-step/spec.md#fr-002  # noqa: E501 - @spec anchor path must stay on one line
                required_evidence.extend(
                    [
                        "convention_domains_recorded",
                        "convention_sources_read",
                        "conventions_applied_to_output",
                    ]
                )
                repair_actions.append(
                    "Read and apply conventions before retrying: "
                    f"domains={', '.join(required_convention_domains)}; "
                    f"sources={', '.join(required_convention_sources)}."
                )
            task: dict[str, Any] = {
                "id": effective_id,
                "ordinal": ordinal,
                "category": category,
                "description": effective_description,
                "required_evidence": required_evidence,
                "invalid_substitutes": list(_invalid_substitutes_for_task(task_id, description)),
                "repair_if_missing": repair_actions,
                "completion_actor": "goal",
                "expected_evidence": {
                    "command": command,
                    "feature_slug": feature_slug,
                },
            }
            if required_conventions is not None:
                task["required_conventions"] = required_conventions
            tasks.append(task)
    return tasks


# @spec FR-001: Per-task convention payload
#   — .specs/features/053-goal-tasks-replay-required-conventions-per-step/spec.md#fr-001
def _task_required_conventions(conventions: Mapping[str, object]) -> RequiredConventions | None:
    selected_domains = [
        domain
        for domain in cast(list[object], conventions.get("selected_domains") or [])
        if isinstance(domain, dict)
    ]
    if not selected_domains:
        return None
    domains = [
        str(domain["name"]) for domain in selected_domains if isinstance(domain.get("name"), str)
    ]
    source_paths = [
        str(path)
        for domain in selected_domains
        for path in cast(list[object], domain.get("paths") or [])
        if isinstance(path, str)
    ]
    if not domains or not source_paths:
        return None
    return {
        "mode": "read_apply",
        "domains": domains,
        "source_paths": source_paths,
    }


def _unique_task_id(base_id: str, seen: set[str], ordinal: int) -> str:
    if base_id not in seen:
        seen.add(base_id)
        return base_id
    task_id = f"{base_id}.{ordinal:03d}"
    seen.add(task_id)
    return task_id


def _task_id_for_description(
    command: str,
    category: str,
    ordinal: int,
    description: str,
) -> str:
    lowered = description.lower()
    if "design fidelity" in lowered:
        return "visual.design_fidelity"
    if "visual-gate validate" in lowered:
        return "visual.gate_validate"
    if "pixel regression" in lowered:
        return "visual.pixel_regression"
    if "staleness gate" in lowered or "baseline.manifest" in lowered:
        return "visual.baseline_manifest"
    # @spec FR-005: route finalize wording to the finalize.registry family
    #   — .specs/features/058-deterministic-finalization/spec.md#fr-005
    if "finalize registry" in lowered or "livespec finalize" in lowered:
        return "finalize.registry"
    if "penflow contract status" in lowered:
        return "penflow.contract_status"
    if "penflow drift" in lowered:
        return "penflow.drift"
    if "compare-report" in lowered:
        return "penflow.compare_report"
    if "spawn independent native sub-agent" in lowered and "/spec-fix" in lowered:
        return "fix.child_goal.spec_fix"
    if "spawn independent native sub-agent" in lowered and "/spec-check" in lowered:
        return "fix.child_goal.spec_check"
    if "capture child" in lowered and "/spec-fix" in lowered:
        return "fix.child_goal.capture"
    if "inspect child goal" in lowered:
        return "fix.child_goal.inspect"
    prefix = "dod" if category == "definition_of_done" else "task"
    slug = _slugify_task_id(description)
    if not slug:
        slug = command
    return f"{prefix}.{ordinal:03d}.{slug}"


def _slugify_task_id(description: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", description.lower()).strip("_")
    slug = re.sub(r"_+", "_", slug)
    return slug[:48].strip("_")


def _required_evidence_for_task(task_id: str, description: str) -> tuple[str, ...]:
    lowered = description.lower()
    if task_id == "visual.design_fidelity":
        return VISUAL_DESIGN_REQUIRED_EVIDENCE
    if task_id == "visual.pixel_regression":
        return ("visual_evidence_receipt_path",)
    if task_id == "finalize.registry":
        return FINALIZE_REQUIRED_EVIDENCE
    if task_id.startswith("fix.child_goal"):
        return (
            "child_goal_hash_recorded",
            "child_contract_file_exists",
            "child_state_file_exists",
            "child_final_status_recorded",
        )
    if "visual-gate validate" in lowered:
        return (
            "command_exit_code_recorded",
            "json_verdict_recorded",
            "missing_artifacts_list_recorded",
        )
    if "penflow" in lowered:
        return (
            "penflow_artifact_path_exists",
            "penflow_status_or_report_recorded",
        )
    if "baseline" in lowered or "mockup" in lowered or "screenshot" in lowered:
        return (
            "artifact_path_exists",
            "hash_or_manifest_status_recorded",
        )
    return GENERIC_REQUIRED_EVIDENCE


def _invalid_substitutes_for_task(task_id: str, description: str) -> tuple[str, ...]:
    if task_id == "visual.design_fidelity":
        return VISUAL_DESIGN_INVALID_SUBSTITUTES
    if task_id == "visual.pixel_regression":
        return ("worker_declared_diff_without_receipt",)
    if task_id == "finalize.registry":
        return FINALIZE_INVALID_SUBSTITUTES
    if "visual" in description.lower():
        return ("verbal_visual_confirmation_without_artifact",)
    return ()


def _repair_actions_for_task(task_id: str, description: str) -> tuple[str, ...]:
    lowered = description.lower()
    if task_id == "visual.design_fidelity":
        return VISUAL_DESIGN_REPAIR_ACTIONS
    if task_id == "visual.pixel_regression":
        return (
            "run `livespec visual-gate certify --feature <slug> --command <command> "
            "--target <target> --run-id <run-id> --json` and submit the generated "
            "receipt.json path",
        )
    if task_id == "finalize.registry":
        return FINALIZE_REPAIR_ACTIONS
    if task_id.startswith("fix.child_goal"):
        return (
            "spawn the required independent native sub-agent and let it create its own goal",
            "record the child goal hash, contract file, state file, final status, and artifacts",
        )
    if "visual-gate validate" in lowered:
        return (
            "run the visual gate command exactly as specified",
            "if exit 7 occurs, create the listed missing artifacts and rerun before proving",
        )
    if "penflow" in lowered:
        return (
            "run the required Penflow command or create the missing Penflow prerequisite",
            "record the concrete Penflow report path and final status",
        )
    return GENERIC_REPAIR_ACTIONS


def _ensure_state_task(
    state: dict[str, Any],
    task: dict[str, Any],
) -> dict[str, Any]:
    tasks = state.setdefault("tasks", {})
    return tasks.setdefault(
        task["id"],
        {
            "ordinal": task["ordinal"],
            "description": task["description"],
            "status": "pending",
            "attempts": [],
            "accepted_evidence": None,
            "last_rejection": None,
        },
    )


def _validate_task_evidence(
    task: dict[str, Any],
    evidence: dict[str, Any],
    *,
    contract: dict[str, Any],
    project_root: Path | None,
) -> dict[str, Any]:
    task_id = str(task["id"])
    if task_id == "visual.design_fidelity" or task_id.startswith(
        ("visual.design_fidelity.", "visual.pixel_regression")
    ):
        return _validate_visual_receipt_evidence(
            task,
            evidence,
            contract=contract,
            project_root=project_root,
        )
    if task_id == "finalize.registry" or task_id.startswith("finalize.registry."):
        return _validate_finalize_receipt_evidence(
            task,
            evidence,
            contract=contract,
            project_root=project_root,
        )
    return _validate_generic_evidence(task, evidence, project_root=project_root)


def _validate_visual_receipt_evidence(
    task: dict[str, Any],
    evidence: dict[str, Any],
    *,
    contract: dict[str, Any],
    project_root: Path | None,
) -> dict[str, Any]:
    missing: list[str] = []
    invalid: list[str] = []
    if "normalized_design_path" in evidence or "normalized_runtime_path" in evidence:
        invalid.append("normalized_json_alignment_only")
    if "comparison_report" in evidence:
        invalid.append("design_alignment_report_as_pixel_report")
    if "actual_diff_percent" in evidence or "verdict" in evidence:
        invalid.append("worker_declared_diff_without_receipt")

    receipt_path = evidence.get("visual_evidence_receipt_path")
    if not isinstance(receipt_path, str) or not receipt_path.strip():
        missing.append("visual_evidence_receipt_path")
    elif project_root is None:
        missing.append("project_root_for_receipt_verification")
    else:
        expected = dict(task.get("expected_evidence") or {})
        expected_feature = expected.get("feature_slug")
        if not isinstance(expected_feature, str) or not expected_feature:
            contract_feature = contract.get("feature")
            expected_feature = contract_feature if isinstance(contract_feature, str) else None
        expected_command = contract.get("command")
        expected_command = expected_command if isinstance(expected_command, str) else None
        expected_target_raw = evidence.get("target")
        expected_target = expected_target_raw if isinstance(expected_target_raw, str) else None
        try:
            receipt = verify_visual_receipt(
                Path(receipt_path),
                project_root=project_root,
                expected_feature_slug=expected_feature,
                expected_command=expected_command,
                expected_target=expected_target,
            )
        except (OSError, VisualReceiptError) as exc:
            missing.append(f"visual_evidence_receipt_valid:{exc}")
        else:
            required_kind = (
                "mockup_runtime"
                if str(task["id"]).startswith("visual.design_fidelity")
                else "baseline_runtime"
            )
            if receipt.verdict != "PASS":
                missing.append("visual_evidence_receipt_verdict_pass")
            if not any(c.comparison_kind == required_kind for c in receipt.comparisons):
                missing.append(f"{required_kind}_comparison_exists")

    accepted = not missing and not invalid
    return {
        "status": "ACCEPTED" if accepted else "REJECTED_NEEDS_ACTION",
        "accepted": accepted,
        "missing_evidence": missing,
        "invalid_substitutes": invalid,
        "required_actions": list(task["repair_if_missing"]),
    }


# @spec FR-005: finalize.registry rejects all substitute evidence,
#   FR-006: verify_finalize_receipt wired into goal prove
#   — .specs/features/058-deterministic-finalization/spec.md#fr-005
def _validate_finalize_receipt_evidence(
    task: dict[str, Any],
    evidence: dict[str, Any],
    *,
    contract: dict[str, Any],
    project_root: Path | None,
) -> dict[str, Any]:
    missing: list[str] = []
    invalid: list[str] = []
    receipt_path = evidence.get("finalize_receipt_path")
    if not isinstance(receipt_path, str) or not receipt_path.strip():
        # Name each substitute so the rejection explains exactly which proxy
        # was offered instead of the receipt (AC-008).
        if evidence.get("output") or evidence.get("prose") or evidence.get("registry_updated"):
            invalid.append("prose_finalization_claim")
        if "exit_code" in evidence:
            invalid.append("exit_code_without_receipt")
        if "files" in evidence or "paths" in evidence or "file_list" in evidence:
            invalid.append("declared_file_list_without_receipt")
        missing.append("finalize_receipt_path")
    elif project_root is None:
        missing.append("project_root_for_receipt_verification")
    else:
        expected = dict(task.get("expected_evidence") or {})
        expected_feature = expected.get("feature_slug")
        if not isinstance(expected_feature, str) or not expected_feature:
            contract_feature = contract.get("feature")
            expected_feature = contract_feature if isinstance(contract_feature, str) else None
        expected_command = contract.get("command")
        expected_command = expected_command if isinstance(expected_command, str) else None
        try:
            receipt = verify_finalize_receipt(
                Path(receipt_path),
                project_root=project_root,
                expected_feature_slug=expected_feature,
                expected_command=expected_command,
            )
        except (OSError, FinalizeReceiptError) as exc:
            missing.append(f"finalize_receipt_valid:{exc}")
        else:
            if receipt.verdict != "PASS":
                missing.append("finalize_receipt_verdict_pass")
    accepted = not missing and not invalid
    return {
        "status": "ACCEPTED" if accepted else "REJECTED_NEEDS_ACTION",
        "accepted": accepted,
        "missing_evidence": missing,
        "invalid_substitutes": invalid,
        "required_actions": list(task["repair_if_missing"]),
    }


def _validate_generic_evidence(
    task: dict[str, Any],
    evidence: dict[str, Any],
    *,
    project_root: Path | None,
) -> dict[str, Any]:
    missing: list[str] = []
    if not evidence:
        missing.extend(task["required_evidence"])
    for required in cast(list[object], task.get("required_evidence") or []):
        if not isinstance(required, str):
            continue
        if required.startswith("convention_") or required == "conventions_applied_to_output":
            satisfied = _convention_evidence_satisfied(task, required, evidence)
        else:
            satisfied = _required_evidence_satisfied(required, evidence, project_root)
        if not satisfied:
            missing.append(required)
    accepted = not missing
    return {
        "status": "ACCEPTED" if accepted else "REJECTED_NEEDS_ACTION",
        "accepted": accepted,
        "missing_evidence": missing,
        "invalid_substitutes": [],
        "required_actions": list(task["repair_if_missing"]),
    }


# @spec FR-003: Validate convention evidence
#   — .specs/features/053-goal-tasks-replay-required-conventions-per-step/spec.md#fr-003
def _convention_evidence_satisfied(
    task: Mapping[str, object],
    required: str,
    evidence: Mapping[str, object],
) -> bool:
    required_conventions = task.get("required_conventions")
    if not isinstance(required_conventions, dict):
        return True
    required_domains = {
        str(domain)
        for domain in cast(list[object], required_conventions.get("domains") or [])
        if isinstance(domain, str)
    }
    required_sources = {
        str(source)
        for source in cast(list[object], required_conventions.get("source_paths") or [])
        if isinstance(source, str)
    }
    if required == "convention_domains_recorded":
        provided_domains = _string_set_evidence(
            evidence,
            ("convention_domains", "convention_domains_recorded"),
        )
        return bool(required_domains) and required_domains.issubset(provided_domains)
    if required == "convention_sources_read":
        provided_sources = _string_set_evidence(
            evidence,
            ("convention_sources", "convention_source_paths", "convention_sources_read"),
        )
        return bool(required_sources) and required_sources.issubset(provided_sources)
    if required == "conventions_applied_to_output":
        return evidence.get(required) is True
    return False


def _string_set_evidence(evidence: Mapping[str, object], keys: tuple[str, ...]) -> set[str]:
    """Collect string or list-of-string evidence values for convention checks."""
    values: set[str] = set()
    for key in keys:
        value = evidence.get(key)
        # Evidence may be one string or a list; other JSON values are invalid proof.
        if isinstance(value, str) and value.strip():
            values.add(value.strip())
        elif isinstance(value, list):
            values.update(item.strip() for item in value if isinstance(item, str) and item.strip())
    return values


def _required_evidence_satisfied(
    required: str,
    evidence: dict[str, Any],
    project_root: Path | None,
) -> bool:
    if required == "observable_output_or_artifact":
        return bool(evidence.get("output")) or _any_evidence_path_exists(
            evidence, ("artifact", "path", "paths", "files"), project_root
        )
    if required == "success_criteria_met":
        return evidence.get("success_criteria_met") is True
    if required == "child_goal_hash_recorded":
        return _nonempty_str(evidence.get("child_goal_hash")) or _nonempty_str(
            evidence.get(required)
        )
    if required == "child_contract_file_exists":
        return _child_goal_artifact_exists(
            evidence,
            (required, "child_contract_file", "contract_file"),
            ".contract.json",
            "contract",
        )
    if required == "child_state_file_exists":
        return _child_goal_artifact_exists(
            evidence,
            (required, "child_state_file", "state_file"),
            ".state.json",
            "state",
        )
    if required == "child_final_status_recorded":
        value = evidence.get("child_final_status", evidence.get(required))
        return isinstance(value, str) and value.lower() in {"complete", "completed", "pass"}
    if required == "command_exit_code_recorded":
        return evidence.get("exit_code", evidence.get(required)) == 0
    if required == "json_verdict_recorded":
        value = evidence.get("json_verdict", evidence.get("verdict"))
        return isinstance(value, str) and value.upper() == "PASS"
    if required == "missing_artifacts_list_recorded":
        value = evidence.get("missing_artifacts", evidence.get(required))
        return isinstance(value, list) and not value
    if required == "penflow_artifact_path_exists":
        return _any_evidence_path_exists(
            evidence, (required, "penflow_artifact_path", "report_path"), project_root
        )
    if required == "penflow_status_or_report_recorded":
        status = evidence.get("penflow_status", evidence.get("status"))
        if isinstance(status, str) and status.upper() in {"PASS", "OK", "SUCCESS", "COMPLETE"}:
            return True
        return _any_evidence_path_exists(evidence, ("report_path",), project_root)
    if required == "artifact_path_exists":
        return _any_evidence_path_exists(
            evidence,
            (required, "artifact", "artifact_path", "path", "paths", "files"),
            project_root,
        )
    if required == "hash_or_manifest_status_recorded":
        digest = evidence.get("sha256", evidence.get("hash"))
        if isinstance(digest, str) and re.fullmatch(r"[a-fA-F0-9]{64}", digest):
            return True
        status = evidence.get("manifest_status")
        return isinstance(status, str) and status.upper() in {"PASS", "OK", "VALID"}
    return evidence.get(required) is True


def _nonempty_str(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _child_goal_artifact_exists(
    evidence: Mapping[str, object],
    keys: tuple[str, ...],
    suffix: str,
    artifact_kind: str,
) -> bool:
    expected_hash = evidence.get("child_goal_hash")
    if not isinstance(expected_hash, str) or not expected_hash.strip():
        return False
    for key in keys:
        value = evidence.get(key)
        values: list[object]
        if isinstance(value, str):
            values = [value]
        elif isinstance(value, list):
            values = cast(list[object], value)
        else:
            values = []
        for item in values:
            if isinstance(item, str) and _valid_child_goal_artifact(
                item, suffix, artifact_kind, expected_hash.strip()
            ):
                # One valid artifact path is enough to satisfy this evidence item.
                return True
    return False


def _valid_child_goal_artifact(
    path_value: str,
    suffix: str,
    artifact_kind: str,
    expected_hash: str,
) -> bool:
    path = Path(path_value)
    if not path.is_absolute() or not path.name.endswith(suffix):
        return False
    if path.parent.name != CHILD_GOAL_ARTIFACT_ROOT_MARKER or not path.name.startswith("goal-"):
        return False
    if not path.exists():
        return False
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        # Invalid or unreadable child goal artifacts cannot prove completion.
        return False
    if not isinstance(payload, dict) or payload.get("goal_hash") != expected_hash:
        return False
    if artifact_kind == "contract":
        return isinstance(payload.get("tasks"), list)
    if artifact_kind == "state":
        status = payload.get("status")
        return isinstance(status, str) and status.lower() in {"complete", "blocked"}
    return False


def _any_evidence_path_exists(
    evidence: dict[str, Any],
    keys: tuple[str, ...],
    project_root: Path | None,
) -> bool:
    for key in keys:
        value = evidence.get(key)
        if isinstance(value, str) and _path_exists(value, project_root):
            return True
        if isinstance(value, list):
            for item in cast(list[object], value):
                if isinstance(item, str) and _path_exists(item, project_root):
                    return True
    return False


def _path_exists(
    path_value: str,
    project_root: Path | None,
) -> bool:
    path = Path(path_value)
    if project_root is not None:
        root = project_root.resolve()
        resolved = path.resolve() if path.is_absolute() else (project_root / path).resolve()
        try:
            resolved.relative_to(root)
        except ValueError:
            return False
        return resolved.exists()
    return path.exists()


def _refresh_state_status(state: dict[str, Any]) -> None:
    tasks = dict(state.get("tasks") or {})
    if tasks and all(task.get("status") == "complete" for task in tasks.values()):
        state["status"] = "complete"
    else:
        state["status"] = "active"


def _compile_conventions_payload(
    *,
    command: str,
    expectations: ExpectationsFile,
    project_root: Path,
    feature: str | None,
    normalized_flags: list[str],
) -> dict[str, Any]:
    """Compile convention domains and source contents into the goal payload."""
    index_path = project_root / ".conventions" / "index.md"
    if not index_path.exists():
        return {
            "available": False,
            "index_path": None,
            "selected_domains": [],
        }
    index_text = index_path.read_text(encoding="utf-8")
    ai_root = _extract_airesources_root(index_text)
    domains = _parse_convention_domains(index_text, ai_root)
    signal_text = _build_convention_signal_text(
        command=command,
        expectations=expectations,
        project_root=project_root,
        feature=feature,
        normalized_flags=normalized_flags,
    )
    selected = [
        domain for domain in domains if _should_select_convention_domain(domain, signal_text)
    ]
    return {
        "available": True,
        "index_path": ".conventions/index.md",
        "selected_domains": [_render_convention_domain(domain, ai_root) for domain in selected],
    }


def _extract_airesources_root(index_text: str) -> Path | None:
    match = re.search(r"\$AIRESOURCES`?\s*=\s*`([^`]+)`", index_text)
    if match is None:
        return None
    return Path(match.group(1))


def _parse_convention_domains(
    index_text: str,
    ai_root: Path | None,
) -> list[dict[str, Any]]:
    domains: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for raw_line in index_text.splitlines():
        line = raw_line.strip()
        heading = re.match(r"^##\s+([^\s\[]+)(?:\s+\[(.*?)\])?", line)
        if heading:
            current = {
                "name": heading.group(1),
                "keywords": _parse_keyword_list(heading.group(2) or ""),
                "refs": [],
            }
            domains.append(current)
            continue
        if current is None or not line.startswith("→"):
            continue
        current["refs"].extend(_parse_convention_refs(line[1:].strip(), ai_root))
    return domains


def _parse_keyword_list(raw_keywords: str) -> list[str]:
    return [keyword.strip() for keyword in raw_keywords.split(",") if keyword.strip()]


def _parse_convention_refs(raw_refs: str, ai_root: Path | None) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    base_dir = ""
    for raw_item in raw_refs.split(","):
        item = raw_item.strip()
        if not item:
            continue
        if item.startswith("$AIRESOURCES/"):
            display_path = item
            base_dir = str(Path(item.removeprefix("$AIRESOURCES/")).parent)
        elif base_dir:
            display_path = f"$AIRESOURCES/{base_dir}/{item}"
        else:
            display_path = item
        refs.append(
            {
                "display_path": display_path,
                "real_path": _resolve_convention_ref(display_path, ai_root),
            }
        )
    return refs


def _resolve_convention_ref(display_path: str, ai_root: Path | None) -> Path | None:
    if display_path.startswith("$AIRESOURCES/"):
        if ai_root is None:
            return None
        return ai_root / display_path.removeprefix("$AIRESOURCES/")
    path = Path(display_path)
    return path if path.is_absolute() else None


# @spec FR-014: Select convention domains from task signal
# — .specs/features/052-deterministic-command-goal-contracts/spec.md#fr-014
def _build_convention_signal_text(
    *,
    command: str,
    expectations: ExpectationsFile,
    project_root: Path,
    feature: str | None,
    normalized_flags: list[str],
) -> str:
    chunks = [
        command,
        feature or "",
        " ".join(normalized_flags),
        *expectations.prose_sections.values(),
    ]
    if feature:
        feature_dir = project_root / ".specs" / "features" / feature
        for filename in CONVENTION_SIGNAL_FILES:
            path = feature_dir / filename
            if path.exists():
                chunks.append(path.read_text(encoding="utf-8"))
    return "\n".join(chunks).lower()


def _should_select_convention_domain(domain: dict[str, Any], signal_text: str) -> bool:
    name = str(domain["name"]).lower()
    keywords = [str(keyword).lower() for keyword in domain["keywords"]]
    if name == "code":
        return True
    if name.startswith("design") and (
        any(word in signal_text for word in DESIGN_SIGNAL_WORDS)
        or any(keyword in signal_text for keyword in keywords)
    ):
        return True
    return any(keyword in signal_text for keyword in keywords)


# @spec FR-015: Embed selected conventions in canonical goal JSON
# — .specs/features/052-deterministic-command-goal-contracts/spec.md#fr-015
def _render_convention_domain(
    domain: dict[str, Any],
    ai_root: Path | None,
) -> dict[str, Any]:
    rendered_files = [_render_convention_file(ref) for ref in domain["refs"]]
    return {
        "name": domain["name"],
        "keywords": list(domain["keywords"]),
        "paths": [str(file["path"]) for file in rendered_files],
        "source_files": rendered_files,
        "airesources_root": ai_root.as_posix() if ai_root is not None else None,
    }


def _render_convention_file(ref: dict[str, Any]) -> dict[str, Any]:
    display_path = str(ref["display_path"])
    real_path = ref["real_path"]
    content = ""
    if isinstance(real_path, Path) and real_path.exists():
        content = real_path.read_text(encoding="utf-8").rstrip()
    return {
        "path": display_path,
        "sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
        "content": content,
    }


def _canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _canonical_rules(rules: list[Rule]) -> list[dict[str, Any]]:
    return [
        {
            "verb": rule.verb,
            "kind": rule.kind,
            "payload": rule.payload,
        }
        for rule in rules
    ]


def _extract_definition_of_done(skill_path: Path) -> list[str]:
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
        if item:
            items.append(item)
    return items


def _normalize_section_lines(section: str) -> list[str]:
    """Normalize prose expectation sections into stable, hashable lines."""
    lines: list[str] = []
    for raw_line in section.splitlines():
        line = " ".join(raw_line.strip().split())
        if not line:
            continue
        lines.append(line)
    return lines


def _stable_path(path: Path, *, project_root: Path, livespec_root: Path) -> str:
    for root in (project_root, livespec_root):
        try:
            return path.resolve().relative_to(root.resolve()).as_posix()
        except ValueError:
            continue
    return path.as_posix()


# Supported goal-contract API used by CLI commands and regression tests.
__all__ = [
    "GoalContract",
    "compile_command_goal",
    "normalize_goal_flags",
    "prove_goal_task",
    "render_goal_contract_file",
    "render_goal_objective",
    "render_goal_state_file",
    "render_goal_status",
    "validate_internal_command_invocation_guards",
]
