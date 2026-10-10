"""Goal hooks responsibilities behind the public contract facade."""

from __future__ import annotations

import hashlib
import shlex
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from . import goal_contracts as _contracts

__all__ = [
    "_archive_run_task",
    "_compile_hooks_payload",
    "_compile_qe_analysis_payload",
    "_hooks_before_task",
    "_qe_analysis_task",
]


def _compile_qe_analysis_payload(
    *,
    command: str,
    livespec_root: Path,
) -> dict[str, Any] | None:
    """Embed the native QE module for commands that own QE-sensitive artifacts."""
    if command not in _contracts.QE_NATIVE_COMMANDS:
        return None
    module_path = livespec_root / _contracts.QE_ANALYSIS_MODULE_PATH
    content = module_path.read_text(encoding="utf-8")
    return {
        "native": True,
        "source_path": _contracts.QE_ANALYSIS_MODULE_PATH.as_posix(),
        "source_sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
        "content": content,
        "commands": sorted(_contracts.QE_NATIVE_COMMANDS),
        "user_hooks_role": "extension_only",
    }


def _compile_hooks_payload(
    *,
    command: str,
    livespec_root: Path,
    project_root: Path,
    feature: str | None,
) -> dict[str, Any]:
    """Compile resolved before-hook context into the goal contract."""
    short_command = _contracts.short_command_name(command)
    command_parts = [
        "livespec",
        "hooks",
        "resolve",
        "--event",
        "before",
        "--command",
        short_command,
    ]
    if feature:
        command_parts.extend(["--feature", feature])
    command_text = " ".join(shlex.quote(part) for part in command_parts)
    try:
        context = _contracts.render_chain_for_stdout(
            "before",
            command,
            feature,
            project_root=project_root,
            commands_dir=livespec_root / ".agent-sync" / "skills",
        )
    except Exception:
        # Match `livespec hooks resolve`: hook resolution is absence-tolerant
        # and must not make goal rendering fail.
        context = ""
    level0_integrations = _resolved_level0_integrations(command, livespec_root)
    return {
        "before": {
            "command": command_text,
            "context": context,
            "context_sha256": hashlib.sha256(context.encode("utf-8")).hexdigest(),
            "level0_integrations": level0_integrations,
            "non_empty": bool(context.strip()),
        }
    }


def _hooks_before_task(*, command: str, hook_context: Mapping[str, object]) -> dict[str, Any]:
    command_text = str(hook_context.get("command") or "")
    sha256 = str(hook_context.get("context_sha256") or "")
    return {
        "id": _contracts.HOOKS_BEFORE_TASK_ID,
        "ordinal": 1,
        "category": "injected",
        "description": f"Resolve and apply before-hook context via `{command_text}`",
        "required_evidence": list(_contracts.HOOKS_BEFORE_REQUIRED_EVIDENCE),
        "invalid_substitutes": list(_contracts.HOOKS_BEFORE_INVALID_SUBSTITUTES),
        "repair_if_missing": list(_contracts.HOOKS_BEFORE_REPAIR_ACTIONS),
        "completion_actor": "goal",
        "expected_evidence": {
            "command": command,
            "hook_resolution_command": command_text,
            "resolved_hook_context_sha256": sha256,
            "feature_slug": None,
        },
    }


# @spec FR-003: Inject qe.analysis task
#   — .specs/features/071-qe-analysis-native-module/spec.md#fr-003
def _qe_analysis_task(*, command: str, next_ordinal: int) -> dict[str, Any]:
    return {
        "id": _contracts.QE_ANALYSIS_TASK_ID,
        "ordinal": next_ordinal,
        "category": "injected",
        "description": "Apply native LiveSpec QE Analysis and record quality evidence contract",
        "required_evidence": list(_contracts.QE_ANALYSIS_REQUIRED_EVIDENCE),
        "invalid_substitutes": list(_contracts.QE_ANALYSIS_INVALID_SUBSTITUTES),
        "repair_if_missing": list(_contracts.QE_ANALYSIS_REPAIR_ACTIONS),
        "completion_actor": "goal",
        "expected_evidence": {
            "command": command,
            "qe_source_path": _contracts.QE_ANALYSIS_MODULE_PATH.as_posix(),
        },
    }


# @spec FR-001: Inject archive.run last ordinal
#   — .specs/features/059-pipeline-verify-phase/spec.md#fr-001
def _archive_run_task(*, command: str, next_ordinal: int) -> dict[str, Any]:
    """Build the synthetic archive.run task injected into every contract.

    Args:
        command: Canonical command name embedded as expected evidence.
        next_ordinal: Strictly highest ordinal — the archive snapshots all
            prior evidence (AC-002).

    Returns:
        The injected task dict. It deliberately carries no convention
        evidence: the task is synthetic compiler work proven by a dedicated
        disk-side validator, not prose execution (AC-003).
    """
    return {
        "id": _contracts.ARCHIVE_RUN_TASK_ID,
        "ordinal": next_ordinal,
        "category": "injected",
        "description": _contracts.ARCHIVE_RUN_TASK_DESCRIPTION,
        "required_evidence": list(_contracts.ARCHIVE_REQUIRED_EVIDENCE),
        "invalid_substitutes": list(_contracts.ARCHIVE_INVALID_SUBSTITUTES),
        "repair_if_missing": list(_contracts.ARCHIVE_REPAIR_ACTIONS),
        "completion_actor": "goal",
        "expected_evidence": {
            "command": command,
            "feature_slug": None,
        },
    }


def _resolved_level0_integrations(command: str, livespec_root: Path) -> list[dict[str, Any]]:
    try:
        level0_integrations = [
            {
                "name": integration.name,
                "path": integration.path.as_posix(),
                "mode": integration.mode,
                "order": integration.order,
            }
            for integration in _contracts.resolve_for(
                "before",
                command,
                commands_dir=livespec_root / ".agent-sync" / "skills",
            )
        ]
    except Exception:
        level0_integrations = []
    return level0_integrations
