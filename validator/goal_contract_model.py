"""Immutable goal contract data and stable evidence family constants."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypeAlias, TypedDict

__all__ = [
    "ALLOWED_INTERNAL_INVOCATION_MODES",
    "ARCHIVE_INVALID_SUBSTITUTES",
    "ARCHIVE_REPAIR_ACTIONS",
    "ARCHIVE_REQUIRED_EVIDENCE",
    "ARCHIVE_RUN_TASK_DESCRIPTION",
    "CHILD_GOAL_ARTIFACT_ROOT_MARKER",
    "CONVENTIONS_REQUIRED_EVIDENCE",
    "CONVENTIONS_VERIFY_COMMAND",
    "CONVENTION_SIGNAL_FILES",
    "DESIGN_SIGNAL_WORDS",
    "EXECUTION_TASK_BRANCHES",
    "FINALIZE_INVALID_SUBSTITUTES",
    "FINALIZE_REPAIR_ACTIONS",
    "FINALIZE_REQUIRED_EVIDENCE",
    "GENERIC_REPAIR_ACTIONS",
    "GENERIC_REQUIRED_EVIDENCE",
    "GOAL_CONTRACT_VERSION",
    "HOOKS_BEFORE_INVALID_SUBSTITUTES",
    "HOOKS_BEFORE_REPAIR_ACTIONS",
    "HOOKS_BEFORE_REQUIRED_EVIDENCE",
    "HOOKS_BEFORE_TASK_ID",
    "INTERNAL_SUBAGENT_GUARD_REQUIREMENTS",
    "MARKDOWN_HORIZONTAL_RULES",
    "QE_ANALYSIS_INVALID_SUBSTITUTES",
    "QE_ANALYSIS_MODULE_PATH",
    "QE_ANALYSIS_REPAIR_ACTIONS",
    "QE_ANALYSIS_REQUIRED_EVIDENCE",
    "QE_ANALYSIS_TASK_ID",
    "QE_NATIVE_COMMANDS",
    "SPEC_CHECK_ALL_FEATURE_FLAGS",
    "VISUAL_DESIGN_INVALID_SUBSTITUTES",
    "VISUAL_DESIGN_REPAIR_ACTIONS",
    "VISUAL_DESIGN_REQUIRED_EVIDENCE",
    "VISUAL_FEATURE_HEADING_RE",
    "_CONVENTIONS_GATED_COMMANDS",
    "GoalContract",
    "RequiredConventions",
    "_TaskEvidenceValidation",
]

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
        "test-report",
        "test-suite",
        "surfaces",
        "quality-only",
        "tree-only",
        "visual-status",
        "multi",
        "fix",
        "fix-execute",
        "fix-feature",
        "fix-conventions",
        "pre-impl",
        "full-check",
        "pre-impl-penflow",
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
# @spec FR-002: archive.run evidence family constants (finalize.registry model)
#   — .specs/features/059-pipeline-verify-phase/spec.md#fr-002
ARCHIVE_REQUIRED_EVIDENCE: tuple[str, ...] = ("run_artifact_path",)
ARCHIVE_INVALID_SUBSTITUTES: tuple[str, ...] = (
    "prose_archive_claim",
    "exit_code_without_artifact",
    "tmpdir_contract_state_paths_without_artifact",
)
ARCHIVE_REPAIR_ACTIONS: tuple[str, ...] = (
    "run `livespec goal archive --contract <c> --state <s> [--feature <slug>]`",
    "resubmit the printed `.specs/.runs/` artifact path as `run_artifact_path`",
)
ARCHIVE_RUN_TASK_DESCRIPTION = (
    "Archive the run via `livespec goal archive` and prove archive.run with the artifact path"
)
HOOKS_BEFORE_TASK_ID = "hooks.before"
HOOKS_BEFORE_REQUIRED_EVIDENCE: tuple[str, ...] = (
    "hook_resolution_command",
    "resolved_hook_context_sha256",
    "hook_context_applied",
)
HOOKS_BEFORE_INVALID_SUBSTITUTES: tuple[str, ...] = (
    "manual_integration_summary",
    "config_file_exists_without_resolved_context",
    "hook_command_mentioned_without_output_hash",
)
HOOKS_BEFORE_REPAIR_ACTIONS: tuple[str, ...] = (
    "run the exact `livespec hooks resolve --event before --command <command> "
    "[--feature <slug>]` command",
    "apply the non-empty stdout as additional command context before continuing",
    "submit the hook command, resolved stdout sha256, and hook_context_applied=true",
)
CONVENTIONS_REQUIRED_EVIDENCE: tuple[str, ...] = ("conventions_receipt_path",)
CONVENTIONS_VERIFY_COMMAND = "livespec conventions verify --json --feature <slug>"
# `spec-feature` supervisors run before the feature scope can exist; their child
# implement/test/fix goals own task-level convention receipts.
_CONVENTIONS_GATED_COMMANDS: frozenset[str] = frozenset(
    {
        "spec-implement",
        "spec-test",
        "spec-fix",
        "spec-ship",
    }
)

# @spec FR-002: Embed native QE for affected commands
#   — .specs/features/071-qe-analysis-native-module/spec.md#fr-002
QE_NATIVE_COMMANDS: frozenset[str] = frozenset({"spec-specify", "spec-plan", "spec-test"})
QE_ANALYSIS_TASK_ID = "qe.analysis"
QE_ANALYSIS_MODULE_PATH = Path("system/qe-analysis.md")

# @spec FR-004: Require structured QE evidence
#   — .specs/features/071-qe-analysis-native-module/spec.md#fr-004
QE_ANALYSIS_REQUIRED_EVIDENCE: tuple[str, ...] = (
    "qe_dimensions_considered",
    "qe_gates_required",
    "qe_expected_evidence",
    "qe_gaps_or_missing_evidence",
    "qe_boundary_note",
)
QE_ANALYSIS_INVALID_SUBSTITUTES: tuple[str, ...] = (
    "generic_quality_claim",
    "skill_global_qe_analysis_invocation",
    "user_config_qe_analysis_only",
)
QE_ANALYSIS_REPAIR_ACTIONS: tuple[str, ...] = (
    "read `system/qe-analysis.md` from the LiveSpec checkout",
    "record the considered quality dimensions, required gates, expected evidence, gaps, "
    "and review/audit/test boundary note",
)

# Match level-2 headings that declare visual/Penflow feature work.
VISUAL_FEATURE_HEADING_RE = re.compile(
    r"^##\s+(Screens|Penflow Contract)\b",
    re.MULTILINE,
)
CHILD_GOAL_ARTIFACT_ROOT_MARKER = "livespec-goals"


class _TaskEvidenceValidation(TypedDict):
    """Describe the closed proof fields consumed by state mutation."""

    status: str
    accepted: bool
    missing_evidence: list[str]
    invalid_substitutes: list[str]
    required_actions: list[str]


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
