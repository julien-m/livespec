"""Deterministic command goal contract compiler.

# @spec FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-007, FR-010, FR-012, FR-013
#   — .specs/features/052-deterministic-command-goal-contracts/spec.md
"""

from __future__ import annotations

import hashlib
import json
import re
import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .command_registry import normalize_command_name
from .exceptions import (
    ArtifactMalformed,
    ExpectationsInvalid,
    ExpectationsMissing,
    OverrideMalformed,
)
from .expectations import ExpectationsFile, Rule, load_expectations
from .run_artifact import find_latest_artifact, read_artifact
from .verify_output import VerifyReport, blocked_report, evaluate

GOAL_CONTRACT_VERSION = "1.0"
CONVENTION_SIGNAL_FILES: tuple[str, ...] = ("spec.md", "plan.md")
EXECUTION_TASK_BRANCHES: frozenset[str] = frozenset(
    {"always", "visual", "penflow", "generate", "visual-generate", "execute"}
)
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


@dataclass(frozen=True)
class GoalVerification:
    """Completion-gate result for a command goal."""

    goal: GoalContract
    report: VerifyReport

    @property
    def outcome(self) -> str:
        """Return the verify-output outcome."""
        return self.report.outcome

    @property
    def exit_code(self) -> int:
        """Return the CLI exit code for this verification."""
        return self.report.exit_code

    def to_json_envelope(self) -> dict[str, Any]:
        """Return the CLI JSON envelope."""
        return {
            "command": self.goal.command,
            "hash": self.goal.goal_hash,
            "outcome": self.report.outcome,
            "exit_code": self.exit_code,
            "expectations": self.goal.payload.get("expectations"),
            "artifact_path": str(self.report.artifact_path)
            if self.report.artifact_path is not None
            else None,
            "blocked_reason": self.report.blocked_reason,
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


def verify_command_goal(
    command: str,
    *,
    project_root: Path,
    livespec_root: Path,
    feature: str | None = None,
    flags: str | list[str] | tuple[str, ...] | None = None,
    run_path: Path | None = None,
) -> GoalVerification:
    """Compile a goal and verify the latest run artifact against it."""
    normalized_command = normalize_command_name(command)
    try:
        goal = compile_command_goal(
            normalized_command,
            project_root=project_root,
            livespec_root=livespec_root,
            feature=feature,
            flags=flags,
        )
    except (ExpectationsInvalid, ExpectationsMissing, OverrideMalformed) as exc:
        goal = _blocked_goal(
            normalized_command,
            project_root=project_root,
            livespec_root=livespec_root,
            feature=feature,
            flags=flags,
            reason=str(exc),
        )
        report = blocked_report(
            command=normalized_command,
            source_path=None,
            artifact_path=run_path,
            reason=str(exc),
        )
        return GoalVerification(goal=goal, report=report)

    expectations = load_expectations(normalized_command, project_root, livespec_root)
    runs_dir = project_root / ".specs" / ".runs"
    artifact_path = run_path or find_latest_artifact(normalized_command, runs_dir)
    if artifact_path is None or not artifact_path.exists():
        report = blocked_report(
            command=normalized_command,
            source_path=expectations.source_path,
            artifact_path=None,
            reason=f"no run artifact found for {normalized_command!r} under {runs_dir}",
        )
        return GoalVerification(goal=goal, report=report)
    try:
        artifact = read_artifact(artifact_path)
    except ArtifactMalformed as exc:
        report = blocked_report(
            command=normalized_command,
            source_path=expectations.source_path,
            artifact_path=artifact_path,
            reason=f"malformed artifact at {exc.path}: {exc.reason}",
        )
        return GoalVerification(goal=goal, report=report)

    normalized_flags = list(goal.payload["normalized_flags"])
    report = evaluate(
        expectations,
        artifact,
        scenario_flags=normalized_flags,
        feature=feature,
        artifact_path=artifact_path,
    )
    return GoalVerification(goal=goal, report=report)


def _detect_visual_feature(project_root: Path, feature: str | None) -> bool:
    """Return True if the feature has visual work (## Screens or ## Penflow Contract)."""
    if feature is None:
        return False
    spec_path = project_root / ".specs" / "features" / feature / "spec.md"
    if not spec_path.exists():
        return False
    # Match level-2 Screens or Penflow Contract headings in spec.md
    return bool(
        re.search(
            r"^##\s+(Screens|Penflow Contract)\b",
            spec_path.read_text(encoding="utf-8"),
            re.MULTILINE,
        )
    )


def _detect_penflow(project_root: Path) -> bool:
    """Return True if a penflow/ directory exists at the project root."""
    return (project_root / "penflow").is_dir()


def _active_execution_task_branches(
    is_visual: bool, visual_enabled: bool, has_penflow: bool, audit_only: bool, no_generate: bool
) -> set[str]:
    """Calculate which execution task branches are active based on context."""
    active: set[str] = {"always"}
    visual_active = is_visual and visual_enabled
    generate_active = not audit_only and not no_generate
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
        is_visual, not no_visual, has_penflow, audit_only, no_generate
    )

    tasks: list[str] = []
    for line in section.splitlines():
        stripped = line.strip()
        # Parse - [branch] task description format
        m = re.match(r"^-\s+\[([^\]]+)\]\s+(.+)$", stripped)
        if m is None:
            continue
        branch = m.group(1).strip()
        if branch not in EXECUTION_TASK_BRANCHES:
            raise ValueError(f"Unknown execution task branch '{branch}' in {skill_path}")
        task = m.group(2).strip()
        if branch in active:
            tasks.append(task)
    return tasks


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
    lines.append("")
    lines.append("Completion gate:")
    lines.append("- Run `livespec goal verify` with the same command, feature, and flags.")
    lines.append("- Call `update_goal(complete)` only when the verification outcome is success.")
    lines.append("- Report blocked or resumable status for drift, error, or blocked outcomes.")
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
    has_penflow = _detect_penflow(project_root)
    execution_tasks = _extract_execution_tasks(
        skill_path,
        normalized_flags=normalized_flags,
        is_visual=is_visual,
        has_penflow=has_penflow,
    )
    payload = {
        "schema_version": GOAL_CONTRACT_VERSION,
        "command": command,
        "feature": feature,
        "normalized_flags": normalized_flags,
        "runtime_context": {
            "is_visual_feature": is_visual,
            "has_penflow": has_penflow,
        },
        "execution_tasks": execution_tasks,
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
        "conventions": _compile_conventions_payload(
            command=command,
            expectations=expectations,
            project_root=project_root,
            feature=feature,
            normalized_flags=normalized_flags,
        ),
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
        "definition_of_done": _extract_definition_of_done(skill_path),
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


def _blocked_goal(
    command: str,
    *,
    project_root: Path,
    livespec_root: Path,
    feature: str | None,
    flags: str | list[str] | tuple[str, ...] | None,
    reason: str,
) -> GoalContract:
    payload = {
        "schema_version": GOAL_CONTRACT_VERSION,
        "command": command,
        "feature": feature,
        "normalized_flags": normalize_goal_flags(flags),
        "blocked_reason": reason,
    }
    canonical_json = _canonical_json(payload)
    goal_hash = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
    project_display = _stable_path(
        project_root,
        project_root=project_root,
        livespec_root=livespec_root,
    )
    return GoalContract(
        command=command,
        payload=payload,
        canonical_json=canonical_json,
        goal_hash=goal_hash,
        objective=(
            f"Goal hash: {goal_hash}\n"
            f"Command: {command}\n"
            f"Feature: {feature or 'none'}\n"
            f"Blocked before goal compilation: {reason}\n"
            f"Project: {project_display}"
        ),
    )


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
        domain
        for domain in domains
        if _should_select_convention_domain(domain, signal_text)
    ]
    return {
        "available": True,
        "index_path": ".conventions/index.md",
        "selected_domains": [
            _render_convention_domain(domain, ai_root)
            for domain in selected
        ],
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
    return [
        keyword.strip()
        for keyword in raw_keywords.split(",")
        if keyword.strip()
    ]


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
    rendered_files = [
        _render_convention_file(ref)
        for ref in domain["refs"]
    ]
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


__all__ = [
    "GoalContract",
    "GoalVerification",
    "compile_command_goal",
    "normalize_goal_flags",
    "render_goal_objective",
    "verify_command_goal",
]
