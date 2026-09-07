"""Goal compile responsibilities behind the public contract facade."""

from __future__ import annotations

import hashlib
import shlex
from pathlib import Path

from . import goal_contracts as _contracts

__all__ = ["_compile_command_goal", "compile_command_goal", "normalize_goal_flags"]


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


# @spec FR-003: Hash the canonical project root
#   — .specs/features/076-spec-init-goal-bootstrap/spec.md#fr-003
def compile_command_goal(
    command: str,
    *,
    project_root: Path,
    livespec_root: Path,
    feature: str | None = None,
    flags: str | list[str] | tuple[str, ...] | None = None,
) -> _contracts.GoalContract:
    """Compile a deterministic goal contract for a LiveSpec command.

    Args:
        command: Command name or alias.
        project_root: Canonical target root. For ``spec-init`` this may be a
            fresh directory without ``.specs``; other commands remain strict.
        livespec_root: LiveSpec checkout root.
        feature: Resolved feature slug, if the command is feature-scoped.
        flags: Active command flags.

    Returns:
        Deterministic :class:`GoalContract`.

    Raises:
        ExpectationsMissing: If no command expectations can be loaded.
        ExpectationsInvalid: If command expectations are invalid.
        OverrideMalformed: If project overrides are malformed.

    Side effects:
        None; compilation reads configuration without creating ``.specs``.
    """
    return _contracts._compile_command_goal(
        command,
        project_root=project_root,
        livespec_root=livespec_root,
        feature=feature,
        flags=flags,
    )


def _compile_command_goal(
    command: str,
    *,
    project_root: Path,
    livespec_root: Path,
    feature: str | None,
    flags: str | list[str] | tuple[str, ...] | None,
) -> _contracts.GoalContract:
    normalized_command = _contracts.normalize_command_name(command)
    expectations = _contracts.load_expectations(
        normalized_command,
        project_root,
        livespec_root,
    )
    payload = _contracts._goal_payload(
        command=normalized_command,
        expectations=expectations,
        livespec_root=livespec_root,
        project_root=project_root,
        feature=feature,
        flags=flags,
    )
    canonical_json = _contracts._canonical_json(payload)
    goal_hash = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
    contract = _contracts.GoalContract(
        command=normalized_command,
        payload=payload,
        canonical_json=canonical_json,
        goal_hash=goal_hash,
        objective="",
    )
    objective = _contracts.render_goal_objective(contract)
    return _contracts.GoalContract(
        command=normalized_command,
        payload=payload,
        canonical_json=canonical_json,
        goal_hash=goal_hash,
        objective=objective,
    )
