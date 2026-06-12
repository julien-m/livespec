# LiveSpec traceability anchors
# @spec(FR-002)
# @spec(FR-003)
# @spec(FR-005)

"""Tests for the deterministic conventions verification engine."""

from __future__ import annotations

import json
import stat
from pathlib import Path

from typer.testing import CliRunner

from validator.cli import app
from validator.conventions_gate import GateSeverity, GateVerdict, verify_conventions

runner = CliRunner()


def _write_project(tmp_path: Path) -> Path:
    specs = tmp_path / ".specs"
    specs.mkdir()
    (specs / "conventions-gates.yaml").write_text(
        """
schema_version: 1
generated_from:
  constitution: .specs/constitution.md
  constitution_sha256: 0000000000000000000000000000000000000000000000000000000000000000
  stack: .specs/stacks/_default.md
commands:
  lint: []
builtin:
  max_file_lines: {target: 4, limit: 6}
  max_function_lines: {target: 3, limit: 5}
  file_header:
    swift: '^//'
    typescript: '^/\\*\\*'
  doc_coverage: {require_public_api: true}
  token_scale: {scale: [2, 4, 8, 12, 16], properties: [padding, margin, spacing]}
  suppression_directives: {budget: 0, whitelist: []}
  import_rules:
    - forbid: {from: "src/ui/**", import: "src/db/**"}
coverage:
  python: full
  typescript: full
  swift: full
exclusions: [".specs/**"]
scope: repo
""",
        encoding="utf-8",
    )
    source = tmp_path / "src"
    (source / "ui").mkdir(parents=True)
    (source / "db").mkdir(parents=True)
    (source / "swift").mkdir(parents=True)
    (source / "ok.py").write_text(
        '"""module."""\n\n\ndef documented() -> None:\n    """Do work."""\n    return None\n',
        encoding="utf-8",
    )
    (source / "ui" / "bad.tsx").write_text(
        "/** module */\n"
        "import { db } from '../db/client';\n"
        "// eslint-disable-next-line\n"
        "export function Card() {\n"
        "  return <div style={{ padding: 10 }}>x</div>;\n"
        "}\n"
        "\n",
        encoding="utf-8",
    )
    (source / "swift" / "Screen.swift").write_text(
        'public func render() {\n    print("x")\n}\n',
        encoding="utf-8",
    )
    return tmp_path


def test_verify_reports_warnings_errors_and_writes_debt_report(tmp_path: Path) -> None:
    project_root = _write_project(tmp_path)

    result = verify_conventions(project_root, report=True)

    assert result.verdict is GateVerdict.FAIL
    assert any(v.severity is GateSeverity.WARNING for v in result.violations)
    assert any(v.severity is GateSeverity.ERROR for v in result.violations)
    assert any(v.rule_id == "builtin.suppression_directives" for v in result.violations)
    assert any(v.rule_id == "builtin.token_scale" for v in result.violations)
    assert any(v.rule_id == "builtin.import_rules" for v in result.violations)
    debt_json = project_root / ".specs" / "conventions" / "debt.json"
    assert debt_json.is_file()
    payload = json.loads(debt_json.read_text(encoding="utf-8"))
    assert payload["verdict"] == "FAIL"
    assert payload["files"][0]["path"].endswith("bad.tsx")


def test_verify_blocks_on_linter_version_mismatch(tmp_path: Path) -> None:
    project_root = _write_project(tmp_path)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    tool = bin_dir / "fake-lint"
    tool.write_text("#!/usr/bin/env sh\necho fake-lint 2.0\n", encoding="utf-8")
    tool.chmod(tool.stat().st_mode | stat.S_IXUSR)
    gates = project_root / ".specs" / "conventions-gates.yaml"
    text = gates.read_text(encoding="utf-8").replace(
        "lint: []",
        f'lint:\n    - id: fake-lint\n      run: "{tool} --json"\n      version: "1.0"',
    )
    gates.write_text(text, encoding="utf-8")

    result = verify_conventions(project_root)

    assert result.verdict is GateVerdict.BLOCKED
    assert result.blockers
    assert "version mismatch" in result.blockers[0].message


def test_delegate_to_declared_command_disables_builtin_threshold(tmp_path: Path) -> None:
    project_root = _write_project(tmp_path)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    tool = bin_dir / "native-lint"
    tool.write_text("#!/usr/bin/env sh\nprintf '[]\\n'\n", encoding="utf-8")
    tool.chmod(tool.stat().st_mode | stat.S_IXUSR)
    gates = project_root / ".specs" / "conventions-gates.yaml"
    text = gates.read_text(encoding="utf-8")
    text = text.replace(
        "lint: []",
        f'lint:\n    - id: native\n      run: "{tool}"',
    )
    text = text.replace(
        "max_file_lines: {target: 4, limit: 6}",
        "max_file_lines: {target: 4, limit: 6, delegate_to: native}",
    )
    gates.write_text(text, encoding="utf-8")

    result = verify_conventions(project_root)

    assert not any(v.rule_id == "builtin.max_file_lines" for v in result.violations)


def test_cli_verify_json_exit_codes_and_gates_init(tmp_path: Path) -> None:
    project_root = _write_project(tmp_path)

    verify_result = runner.invoke(
        app,
        ["conventions", "verify", "--repo", str(project_root), "--json"],
    )

    assert verify_result.exit_code == 1
    payload = json.loads(verify_result.output)
    assert payload["verdict"] == "FAIL"

    fresh = tmp_path / "fresh"
    (fresh / ".specs" / "stacks").mkdir(parents=True)
    (fresh / ".specs" / "constitution.md").write_text("# Constitution\n", encoding="utf-8")
    (fresh / ".specs" / "stacks" / "_default.md").write_text("Python CLI\n", encoding="utf-8")

    init_result = runner.invoke(app, ["conventions", "gates", "init", "--repo", str(fresh)])

    assert init_result.exit_code == 0, init_result.output
    assert (fresh / ".specs" / "conventions-gates.yaml").is_file()


def test_cli_scaffold_sync_limits_updates_swiftlint_config(tmp_path: Path) -> None:
    project_root = _write_project(tmp_path)
    swiftlint = project_root / ".swiftlint.yml"
    swiftlint.write_text("file_length:\n  warning: 1\n  error: 2\n", encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "conventions",
            "scaffold",
            "--repo",
            str(project_root),
            "--apply",
            "--sync-limits",
        ],
    )

    assert result.exit_code == 0, result.output
    text = swiftlint.read_text(encoding="utf-8")
    assert "warning: 4" in text
    assert "error: 6" in text
    assert "function_body_length" in text
