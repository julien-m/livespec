# @spec(FR-013)
# .specs/features/078-requirement-evidence-integrity/spec.md#fr-013
"""Native runtime profiles shared by bounded direct and full-workflow generation."""

from __future__ import annotations

import math


def generation_arguments(
    runtime: str,
    executable: str,
    prompt: str,
    *,
    workflow: bool = False,
    max_budget_usd: float = 5,
) -> list[str]:
    """Use native authenticated CLIs; API-key presence is not an auth probe."""
    if not math.isfinite(max_budget_usd) or max_budget_usd <= 0:
        raise ValueError("max_budget_usd must be finite and positive")
    if runtime == "codex":
        return [
            executable,
            "exec",
            "--json",
            *([] if workflow else ["--ephemeral"]),
            "--ignore-user-config",
            "--skip-git-repo-check",
            "--sandbox",
            "workspace-write",
            prompt,
        ]
    if runtime == "claude":
        return [
            executable,
            "--print",
            "--output-format",
            "json",
            "--max-budget-usd",
            str(max_budget_usd),
            "--max-turns",
            "80" if workflow else "12",
            "--permission-mode",
            "bypassPermissions" if workflow else "acceptEdits",
            "--allowedTools",
            "Read,Write,Edit,Bash,Glob,Grep,Agent,Task"
            if workflow
            else "Read,Write,Edit,Glob,Grep",
            "--",
            prompt,
        ]
    raise ValueError(f"Unsupported runtime: {runtime}")
