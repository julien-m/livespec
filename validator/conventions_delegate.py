# LiveSpec traceability anchors
# @spec(FR-002)

"""Rule-specific delegate_to capability checks."""

from __future__ import annotations

from .conventions_gates import CommandGroups

_LINTER_RULE_CAPABILITIES: dict[str, frozenset[str]] = {
    "swiftlint": frozenset({"builtin.max_file_lines", "builtin.max_function_lines"}),
    "eslint": frozenset({"builtin.max_file_lines"}),
}


def is_rule_delegated(commands: CommandGroups, delegate_to: str | None, rule_id: str) -> bool:
    """Return whether `delegate_to` names a command that covers `rule_id`."""
    if not delegate_to:
        return False
    return any(
        command.id == delegate_to
        and rule_id in _LINTER_RULE_CAPABILITIES.get(command.id, frozenset())
        for command in commands.lint + commands.format + commands.typecheck
    )
