"""Test generation requires readiness, while inspection and existing-test modes do not."""

from pathlib import Path

import pytest

from validator.goal_contracts import compile_command_goal

REPO = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    "flags,generates",
    [
        ("", True),
        ("--no-generate", False),
        ("--audit-only", False),
        ("--dry-run", False),
        ("--regenerate-missing", False),
        ("--regenerate-missing --confirm", True),
        ("--regenerate-missing --confirm --dry-run", False),
    ],
)
def test_generation_readiness_precedes_writes_only_in_writing_modes(
    tmp_path: Path, flags: str, generates: bool
) -> None:
    feature = tmp_path / ".specs/features/001-tests"
    feature.mkdir(parents=True)
    (feature / "spec.md").write_text("# Tests\n## Acceptance Criteria\n### AC-001\nBehavior.\n")
    goal = compile_command_goal(
        "spec-test",
        project_root=tmp_path,
        livespec_root=REPO,
        feature=feature.name,
        flags=f"{flags} --model=reviewer/v1",
    )
    tasks = goal.payload["tasks"]
    gates = [task for task in tasks if "test-generation readiness" in task["description"]]
    assert bool(gates) is generates
    if generates:
        gate = gates[0]
        assert "--progression implement" in gate["description"]
        assert "--model" in gate["description"] and "--review-max-chars" in gate["description"]
        assert "execution_receipt_path" not in gate["required_evidence"]
        first_write = next(task for task in tasks if task["description"].startswith("Write tests:"))
        assert gate["ordinal"] < first_write["ordinal"]
    else:
        assert not any(task["description"].startswith("Write tests:") for task in tasks)


@pytest.mark.parametrize(
    "section",
    [
        "## Phase 3 — Generate",
        "### 4.5.1 — Generate Missing Visual Test Files",
        "## --regenerate-missing Flag",
    ],
)
def test_all_generation_entrypoints_reference_the_same_readiness_gate(section: str) -> None:
    skill = (REPO / ".agent-sync/skills/spec-test/SKILL.md").read_text()
    start = skill.index(section)
    boundary = skill.find("\n## ", start + len(section))
    text = skill[start : boundary if boundary >= 0 else len(skill)]
    assert "#test-generation-readiness" in text
