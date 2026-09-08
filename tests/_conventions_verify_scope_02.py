"""Preserved test cases and fixtures for test_conventions_verify_scope.py."""

from __future__ import annotations

import json
from pathlib import Path

from tests._conventions_verify_scope_01 import (
    FEATURE,
    _convention_evidence,
    _invoke_verify,
    _write_empty_gates,
    _write_feature_scope,
    _write_project,
    runner,
)
from tests.test_goal_contracts import (
    EXECUTION_TASK_SKILL,
    EXPECTATIONS,
    _fixture_roots,
    _write_conventions,
)
from validator.cli import app
from validator.goal_contracts import (
    compile_command_goal,
    prove_goal_task,
    render_goal_contract_file,
    render_goal_state_file,
)


def test_goal_prove_accepts_cli_generated_pass_conventions_receipt(tmp_path: Path) -> None:
    project_root, livespec_root = _fixture_roots(tmp_path)
    _write_conventions(project_root, tmp_path / "ai")
    _write_empty_gates(project_root)
    (project_root / "src").mkdir()
    (project_root / "src" / "demo.py").write_text('"""Demo module."""\n', encoding="utf-8")
    _write_feature_scope(project_root, "001-demo", ["src/demo.py"])
    skill_dir = livespec_root / ".agent-sync" / "skills" / "spec-implement"
    skill_dir.mkdir(parents=True)
    (skill_dir / "expectations.md").write_text(
        EXPECTATIONS.replace("command: spec-demo", "command: spec-implement"),
        encoding="utf-8",
    )
    (skill_dir / "SKILL.md").write_text(EXECUTION_TASK_SKILL, encoding="utf-8")
    cli_result = _invoke_verify(project_root, "001-demo", "goal-pass")
    assert cli_result.exit_code == 0, cli_result.output
    receipt_path = json.loads(cli_result.output)["receipt_path"]
    goal = compile_command_goal(
        "spec-implement",
        project_root=project_root,
        livespec_root=livespec_root,
        feature="001-demo",
    )
    contract = json.loads(render_goal_contract_file(goal))
    state = json.loads(render_goal_state_file(goal))
    task_id = next(
        task["id"]
        for task in contract["tasks"]
        if "conventions_receipt_path" in task["required_evidence"]
    )

    result = prove_goal_task(
        contract,
        state,
        task_id,
        evidence=_convention_evidence(receipt_path),
        project_root=project_root,
    )

    assert result["status"] == "ACCEPTED"


def test_feature_scope_ignores_legacy_artifact_links_when_current_mapping_is_clean(
    tmp_path: Path,
) -> None:
    project_root = _write_project(tmp_path)
    (project_root / "src").mkdir(exist_ok=True)
    (project_root / "src" / "current.py").write_text('"""Current module."""\n', encoding="utf-8")
    (project_root / "src" / "legacy.py").write_text(
        '"""Legacy module."""\n'
        "\n"
        "\n"
        "def legacy_scope() -> None:\n"
        '    """Do legacy work."""\n'
        "    first = 1\n"
        "    second = 2\n"
        "    third = 3\n"
        "    return None\n",
        encoding="utf-8",
    )
    feature_dir = project_root / ".specs" / "features" / "063-conventions-blocking-pipeline"
    feature_dir.mkdir(parents=True)
    (feature_dir / "implementation.md").write_text(
        "## Requirement Mapping\n\n"
        "| Requirement | File(s) | @spec Anchor | Status | Last Verified |\n"
        "|---|---|---|---|---|\n"
        "| FR-001 | [`src/current.py`](../../../src/current.py) | scoped | Implemented | now |\n",
        encoding="utf-8",
    )
    (feature_dir / "changelog.md").write_text(
        "## 2026-06-01 — Historical work\n\n"
        "- Updated [`src/legacy.py`](../../../src/legacy.py) in an older cycle.\n",
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        [
            "conventions",
            "verify",
            "--repo",
            str(project_root),
            "--json",
            "--feature",
            "063-conventions-blocking-pipeline",
            "--run-id",
            "legacy-links",
        ],
    )

    assert result.exit_code == 0, result.output
    output = json.loads(result.output)
    assert output["verdict"] == "PASS"
    assert output["violations"] == []


def test_feature_scope_ignores_frontmatter_dates_when_mapping_rows_are_undated(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    _write_conventions(project_root, tmp_path / "ai")
    _write_empty_gates(project_root)
    (project_root / "src").mkdir()
    (project_root / "src" / "scoped.py").write_text('"""Scoped module."""\n', encoding="utf-8")
    feature_dir = project_root / ".specs" / "features" / FEATURE
    feature_dir.mkdir(parents=True)
    (feature_dir / "implementation.md").write_text(
        "---\n"
        "created: 2026-06-29\n"
        "updated: 2026-06-29\n"
        "---\n\n"
        "## Requirement Mapping\n\n"
        "| Requirement | File(s) | @spec Anchor | Status | Last Verified |\n"
        "|---|---|---|---|---|\n"
        "| FR-001 | [`src/scoped.py`](../../../src/scoped.py) | scoped | Implemented | now |\n",
        encoding="utf-8",
    )

    result = _invoke_verify(project_root, FEATURE, "frontmatter-dates")

    assert result.exit_code == 0, result.output
    output = json.loads(result.output)
    assert output["verdict"] == "PASS"
