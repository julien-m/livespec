# LiveSpec traceability anchors
# @spec(FR-002)

"""Rule-specific delegate_to capability checks."""

from __future__ import annotations

from .conventions_gates import CommandGroups, GateCommand

_LINTER_RULE_CAPABILITIES: dict[str, frozenset[str]] = {
    "swiftlint": frozenset({"builtin.max_file_lines", "builtin.max_function_lines"}),
    "eslint": frozenset({"builtin.max_file_lines"}),
}


def is_rule_delegated(commands: CommandGroups, delegate_to: str | None, rule_id: str) -> bool:
    """Return whether `delegate_to` names a command that covers `rule_id`."""
    if not delegate_to:
        return False
    return any(
        command.id == delegate_to and _command_covers_rule(command, rule_id)
        for command in commands.lint + commands.format + commands.typecheck
    )


def _command_covers_rule(command: GateCommand, rule_id: str) -> bool:
    if rule_id in _LINTER_RULE_CAPABILITIES.get(command.id, frozenset()):
        return True
    return any(
        wiring.get("kind") in {"covers_rule", "rule_coverage"} and wiring.get("rule") == rule_id
        for wiring in command.wiring
    )
