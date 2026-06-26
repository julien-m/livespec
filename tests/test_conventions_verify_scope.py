"""Regression tests for feature-scoped conventions verification."""

from __future__ import annotations

import json
import stat
import subprocess
from hashlib import sha256
from pathlib import Path

from typer.testing import CliRunner

from tests.test_goal_contracts import (
    EXECUTION_TASK_SKILL,
    EXPECTATIONS,
    _fixture_roots,
    _write_conventions,
)
from validator.cli import app
from validator.conventions_gates import gates_path
from validator.conventions_receipt import verify_conventions_receipt
from validator.goal_contracts import (
    compile_command_goal,
    prove_goal_task,
    render_goal_contract_file,
    render_goal_state_file,
)

runner = CliRunner()
FEATURE = "063-conventions-blocking-pipeline"


def _write_project(tmp_path: Path) -> Path:
    specs = tmp_path / ".specs"
    specs.mkdir()
    constitution = specs / "constitution.md"
    constitution.write_text("# Constitution\n", encoding="utf-8")
    constitution_sha = sha256(constitution.read_bytes()).hexdigest()
    (specs / "conventions-gates.yaml").write_text(
        f"""\
schema_version: 1
generated_from:
  constitution: .specs/constitution.md
  constitution_sha256: {constitution_sha}
  stack: .specs/stacks/_default.md
commands:
  lint: []
builtin:
  max_file_lines: {{target: 4, limit: 6}}
  max_function_lines: {{target: 3, limit: 5}}
  file_header:
    typescript: '^/\\*\\*'
  doc_coverage: {{require_public_api: true}}
  token_scale: {{scale: [2, 4, 8, 12, 16], properties: [padding, margin, spacing]}}
  suppression_directives: {{budget: 0, whitelist: []}}
  import_rules: []
coverage:
  python: full
  typescript: full
exclusions: [".specs/**"]
scope: repo
""",
        encoding="utf-8",
    )
    source = tmp_path / "src"
    (source / "ui").mkdir(parents=True)
    (source / "db").mkdir(parents=True)
    (source / "ui" / "bad.tsx").write_text(
        "/** module */\n"
        "import { db } from '../db/client';\n"
        "// eslint-disable-next-line\n"
        "export function Card() {\n"
        "  return <div style={{ padding: 12 }}>x</div>;\n"
        "}\n"
        "\n",
        encoding="utf-8",
    )
    return tmp_path


def _write_feature_scope(project_root: Path, feature_slug: str, paths: list[str]) -> None:
    feature_dir = project_root / ".specs" / "features" / feature_slug
    feature_dir.mkdir(parents=True, exist_ok=True)
    rows = "\n".join(
        f"| FR-{index:03d} | [`{path}`](../../../{path}) | scoped | Implemented | now |"
        for index, path in enumerate(paths, start=1)
    )
    (feature_dir / "implementation.md").write_text(
        "## Requirement Mapping\n\n"
        "| Requirement | File(s) | @spec Anchor | Status | Last Verified |\n"
        "|---|---|---|---|---|\n"
        f"{rows}\n",
        encoding="utf-8",
    )


def _write_empty_gates(project_root: Path) -> Path:
    path = gates_path(project_root)
    constitution = project_root / ".specs" / "constitution.md"
    constitution.parent.mkdir(parents=True, exist_ok=True)
    constitution.write_text("# Constitution\n", encoding="utf-8")
    path.write_text(
        f"""\
schema_version: 1
generated_from:
  constitution: .specs/constitution.md
  constitution_sha256: {sha256(constitution.read_bytes()).hexdigest()}
  stack: .specs/stacks/_default.md
commands: {{}}
builtin: {{}}
coverage: {{}}
exclusions: []
scope: repo
""",
        encoding="utf-8",
    )
    return path


def _commit_all(project_root: Path) -> None:
    subprocess.run(["git", "init"], cwd=project_root, check=True, capture_output=True)
    subprocess.run(["git", "add", "."], cwd=project_root, check=True, capture_output=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=LiveSpec Test",
            "-c",
            "user.email=livespec-test@example.com",
            "commit",
            "-m",
            "initial",
        ],
        cwd=project_root,
        check=True,
        capture_output=True,
    )


def _invoke_verify(project_root: Path, feature: str | None, run_id: str | None):
    args = ["conventions", "verify", "--repo", str(project_root), "--json"]
    if feature is not None:
        args.extend(["--feature", feature])
    if run_id is not None:
        args.extend(["--run-id", run_id])
    return runner.invoke(app, args)


def test_cli_verify_feature_writes_pass_conventions_receipt(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    _write_conventions(project_root, tmp_path / "ai")
    _write_empty_gates(project_root)
    (project_root / "src").mkdir()
    (project_root / "src" / "scoped.py").write_text('"""Scoped module."""\n', encoding="utf-8")
    _write_feature_scope(project_root, FEATURE, ["src/scoped.py"])

    result = _invoke_verify(project_root, FEATURE, "run-pass")

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["verdict"] == "PASS"
    assert payload["feature_slug"] == FEATURE
    assert payload["run_id"] == "run-pass"
    assert payload["receipt_path"] == ".specs/conventions/runs/run-pass/receipt.json"
    receipt = verify_conventions_receipt(
        project_root / payload["receipt_path"],
        project_root=project_root,
        expected_feature_slug=FEATURE,
    )
    assert receipt.verdict == "PASS"


def test_cli_verify_feature_scopes_violations_and_receipt_to_implementation_files(
    tmp_path: Path,
) -> None:
    project_root = _write_project(tmp_path)
    (project_root / "src" / "scoped.py").write_text('"""Scoped module."""\n', encoding="utf-8")
    _write_feature_scope(project_root, FEATURE, ["src/scoped.py"])
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    tool = bin_dir / "lint-json"
    payload = json.dumps(
        [{"filename": "src/ui/bad.tsx", "location": {"row": 2}, "code": "X001", "message": "debt"}]
    )
    tool.write_text(f"#!/usr/bin/env sh\nprintf '%s\\n' '{payload}'\nexit 1\n", encoding="utf-8")
    tool.chmod(tool.stat().st_mode | stat.S_IXUSR)
    gates = project_root / ".specs" / "conventions-gates.yaml"
    gates.write_text(
        gates.read_text(encoding="utf-8").replace(
            "lint: []",
            f'lint:\n    - id: lint-json\n      run: "{tool}"',
        ),
        encoding="utf-8",
    )

    result = _invoke_verify(project_root, FEATURE, "scoped-pass")

    assert result.exit_code == 0, result.output
    output = json.loads(result.output)
    assert output["verdict"] == "PASS"
    assert output["violations"] == []
    assert output["receipt_path"] == ".specs/conventions/runs/scoped-pass/receipt.json"


def test_cli_verify_repo_pseudo_scope_writes_repo_wide_receipt(tmp_path: Path) -> None:
    project_root = _write_project(tmp_path)

    result = _invoke_verify(project_root, "repo", "repo-scope")

    assert result.exit_code == 1, result.output
    output = json.loads(result.output)
    assert output["feature_slug"] == "repo"
    assert output["receipt_path"] == ".specs/conventions/runs/repo-scope/receipt.json"
    assert any(item["path"] == "src/ui/bad.tsx" for item in output["violations"])
    receipt = verify_conventions_receipt(
        project_root / output["receipt_path"],
        project_root=project_root,
        expected_feature_slug="repo",
    )
    assert receipt.verdict == "FAIL"


def test_cli_verify_feature_scope_includes_latest_dated_mapping_only(tmp_path: Path) -> None:
    project_root = _write_project(tmp_path)
    (project_root / "src" / "old.py").write_text(_violating_python("old_scope"), encoding="utf-8")
    (project_root / "src" / "current.py").write_text(
        _violating_python("current_scope"), encoding="utf-8"
    )
    feature_dir = project_root / ".specs" / "features" / FEATURE
    feature_dir.mkdir(parents=True)
    (feature_dir / "implementation.md").write_text(
        "| Requirement | File(s) | @spec Anchor | Status | Last Verified |\n"
        "|---|---|---|---|---|\n"
        "| FR-001 | [`src/old.py`](../../../src/old.py) | scoped | Implemented | 2026-06-13 |\n"
        "| FR-002 | [`src/current.py`](../../../src/current.py) | scoped | "
        "Implemented | 2026-06-25 |\n",
        encoding="utf-8",
    )

    result = _invoke_verify(project_root, FEATURE, "scope-current")

    assert result.exit_code == 1, result.output
    output = json.loads(result.output)
    assert any(item["path"] == "src/current.py" for item in output["violations"])
    assert not any(item["path"] == "src/old.py" for item in output["violations"])


def test_cli_verify_feature_scope_includes_dirty_source_when_feature_artifacts_changed(
    tmp_path: Path,
) -> None:
    project_root = _write_project(tmp_path)
    dirty_source = project_root / "src" / "current.py"
    dirty_source.write_text('"""Current module."""\n', encoding="utf-8")
    (project_root / "src" / "scoped.py").write_text('"""Scoped module."""\n', encoding="utf-8")
    _write_feature_scope(project_root, FEATURE, ["src/scoped.py"])
    _commit_all(project_root)
    dirty_source.write_text(_violating_python("current_scope"), encoding="utf-8")
    feature_artifact = project_root / ".specs" / "features" / FEATURE / "implementation.md"
    feature_artifact.write_text(feature_artifact.read_text(encoding="utf-8") + "\n- Current.\n")

    result = _invoke_verify(project_root, FEATURE, "dirty-scope")

    assert result.exit_code == 1, result.output
    output = json.loads(result.output)
    assert any(item["path"] == "src/current.py" for item in output["violations"])
    assert not any(item["path"] == "src/ui/bad.tsx" for item in output["violations"])


def test_cli_verify_unscoped_json_stays_repo_wide_with_unrelated_debt(tmp_path: Path) -> None:
    project_root = _write_project(tmp_path)
    _write_feature_scope(project_root, FEATURE, ["src/scoped.py"])

    result = _invoke_verify(project_root, None, None)

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert any(item["path"] == "src/ui/bad.tsx" for item in output["violations"])
    assert "receipt_path" not in output


def test_spec_check_conventions_gate_can_use_feature_scoped_pass_receipt(tmp_path: Path) -> None:
    project_root = _write_project(tmp_path)
    (project_root / "src" / "scoped.py").write_text('"""Scoped module."""\n', encoding="utf-8")
    _write_feature_scope(project_root, FEATURE, ["src/scoped.py"])

    result = _invoke_verify(project_root, FEATURE, "spec-check-gate")

    assert result.exit_code == 0, result.output
    output = json.loads(result.output)
    assert output["feature_slug"] == FEATURE
    receipt = verify_conventions_receipt(
        project_root / output["receipt_path"],
        project_root=project_root,
        expected_feature_slug=FEATURE,
    )
    assert receipt.verdict == "PASS"


def test_cli_verify_invalid_feature_inputs_block_without_receipt(tmp_path: Path) -> None:
    project_root = _write_project(tmp_path)

    missing = _invoke_verify(project_root, "999-missing-feature", "missing-feature")
    traversal = _invoke_verify(project_root, "../escape", "bad-feature")

    assert missing.exit_code == 2
    assert json.loads(missing.output)["receipt_path"] is None
    assert traversal.exit_code == 2
    assert json.loads(traversal.output)["receipt_path"] is None
    assert not (project_root / ".specs" / "conventions" / "runs").exists()


def test_cli_verify_feature_writes_fail_conventions_receipt(tmp_path: Path) -> None:
    project_root = _write_project(tmp_path)
    _write_feature_scope(project_root, FEATURE, ["src/ui/bad.tsx"])

    result = _invoke_verify(project_root, FEATURE, "run-fail")

    assert result.exit_code == 1, result.output
    payload = json.loads(result.output)
    assert payload["verdict"] == "FAIL"
    assert payload["receipt_path"] == ".specs/conventions/runs/run-fail/receipt.json"
    receipt = verify_conventions_receipt(
        project_root / payload["receipt_path"],
        project_root=project_root,
        expected_feature_slug=FEATURE,
    )
    assert receipt.verdict == "FAIL"


def test_cli_verify_rejects_run_id_path_traversal_before_writing_receipt(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    _write_conventions(project_root, tmp_path / "ai")
    _write_empty_gates(project_root)
    (project_root / "src").mkdir()
    (project_root / "src" / "scoped.py").write_text('"""Scoped module."""\n', encoding="utf-8")
    _write_feature_scope(project_root, FEATURE, ["src/scoped.py"])

    result = _invoke_verify(project_root, FEATURE, "../escape")

    assert result.exit_code == 2
    payload = json.loads(result.output)
    assert payload["blockers"] == ["invalid run_id: ../escape"]
    assert payload["receipt_path"] is None
    assert not (project_root / ".specs" / "conventions" / "runs").exists()


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

    result = prove_goal_task(
        contract,
        state,
        contract["tasks"][0]["id"],
        evidence=_convention_evidence(receipt_path),
        project_root=project_root,
    )

    assert result["status"] == "ACCEPTED"


def _violating_python(name: str) -> str:
    return (
        '"""Current module."""\n\n\n'
        f"def {name}() -> None:\n"
        '    """Do current work."""\n'
        "    first = 1\n"
        "    second = 2\n"
        "    third = 3\n"
        "    return None\n"
    )


def _convention_evidence(receipt_path: str) -> dict[str, object]:
    return {
        "output": "done",
        "success_criteria_met": True,
        "convention_domains": ["code"],
        "convention_sources": [
            "$AIRESOURCES/code-conventions/general.md",
            "$AIRESOURCES/code-conventions/python.md",
        ],
        "conventions_applied_to_output": True,
        "conventions_receipt_path": receipt_path,
    }


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
