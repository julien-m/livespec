"""Keep explicit goal diagnostics stable after shortening default skills."""

from pathlib import Path

import pytest

from tests._goal_contracts_01 import (
    INLINE_INTERNAL_COMMAND_SKILL,
    SUBAGENT_INTERNAL_COMMAND_SKILL,
    _fixture_roots,
)
from validator.exceptions import ExpectationsInvalid
from validator.goal_contracts import compile_command_goal


def test_explicit_goal_uses_preserved_inventory(tmp_path: Path) -> None:
    """A compact delivery skill must not change its historical goal inventory."""
    project, source = _fixture_roots(tmp_path)
    skill_dir = next((source / ".agent-sync/skills").iterdir())
    command = skill_dir.name
    skill = skill_dir / "SKILL.md"
    skill.write_text(SUBAGENT_INTERNAL_COMMAND_SKILL)
    before = compile_command_goal(command, project_root=project, livespec_root=source)

    skill.rename(skill_dir / "certification.md")
    skill.write_text("# Delivery\nImplement, check and obtain independent final review.\n")
    after = compile_command_goal(command, project_root=project, livespec_root=source)

    for key in ("execution_tasks", "definition_of_done", "internal_command_invocations", "tasks"):
        assert after.payload[key] == before.payload[key]


def test_explicit_goal_does_not_hide_invalid_diagnostic_inventory(tmp_path: Path) -> None:
    """An invalid archived diagnostic must fail instead of using the normal skill."""
    project, source = _fixture_roots(tmp_path)
    skill_dir = next((source / ".agent-sync/skills").iterdir())
    (skill_dir / "certification.md").write_text(INLINE_INTERNAL_COMMAND_SKILL)

    with pytest.raises(ExpectationsInvalid, match="inline"):
        compile_command_goal(skill_dir.name, project_root=project, livespec_root=source)
