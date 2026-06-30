"""Tests for AST convention rollout mode behavior."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path

from validator.conventions_ast.backends.fake import FakeAstBackend
from validator.conventions_ast.engine import run_ast_conventions
from validator.conventions_ast.models import AstMatch
from validator.conventions_gates import load_conventions_gates

# Minimal executable AST catalogue used by rollout-mode tests.
AST_HIGH_CATALOG_TEMPLATE = """\
rules:
  - id: ts.no_as_any
    title: No as any
    language: typescript
    domain: code
    decision_kind: executable
    decidability: ast
    precision: high
    severity: error
    source_path: {source_path}
    source_anchor: "#typescript-specifics"
    source_hash: sha256:{source_hash}
    backend: ast-grep
    detector: ts.no_as_any
    patterns:
      - kind: sg_yaml
        value: "rule: {{ pattern: '$A as any' }}"
    fixtures:
      pass: tests/fixtures/pass.ts
      fail: tests/fixtures/fail.ts
    deterministic_test_evidence:
      - test: tests/test_conventions_ast_multilang.py
        pass_fixture: tests/fixtures/pass.ts
        fail_fixture: tests/fixtures/fail.ts
    justification:
      required: true
      accepted_window: adjacent_comment_block
      rule_id_required: true
"""

AST_GATES_TEMPLATE = """\
schema_version: 2
generated_from:
  constitution: .specs/constitution.md
  constitution_sha256: {constitution_hash}
  stack: .specs/stacks/_default.md
commands: {{lint: []}}
builtin: {{}}
coverage: {{}}
exclusions: [".specs/**"]
scope: repo
ast_rules:
  mode: {mode}
  backend:
    name: ast-grep
    command: sg
  catalogs:
    - validator/conventions_ast/rule_catalog/ast_high.yaml
"""


def _write_v2_project(tmp_path: Path, mode: str) -> tuple[Path, Path]:
    specs = tmp_path / ".specs"
    specs.mkdir(parents=True)
    constitution = specs / "constitution.md"
    constitution.write_text("# Constitution\n", encoding="utf-8")
    source = tmp_path / "src" / "bad.ts"
    source.parent.mkdir()
    source.write_text("const value = input as any;\n", encoding="utf-8")
    fixture_pass = tmp_path / "tests" / "fixtures" / "pass.ts"
    fixture_fail = tmp_path / "tests" / "fixtures" / "fail.ts"
    fixture_pass.parent.mkdir(parents=True)
    fixture_pass.write_text("const value = input as unknown;\n", encoding="utf-8")
    fixture_fail.write_text("const value = input as any;\n", encoding="utf-8")
    test_file = tmp_path / "tests" / "test_conventions_ast_multilang.py"
    test_file.write_text("def test_fixture_contract():\n    assert True\n", encoding="utf-8")
    catalog = tmp_path / "validator" / "conventions_ast" / "rule_catalog" / "ast_high.yaml"
    catalog.parent.mkdir(parents=True)
    js_source = tmp_path / "ai-ressources" / "code-conventions" / "javascript.md"
    js_source.parent.mkdir(parents=True)
    js_source.write_text("# TypeScript Specifics\n\nany is forbidden.\n", encoding="utf-8")
    catalog.write_text(
        AST_HIGH_CATALOG_TEMPLATE.format(
            source_path=js_source,
            source_hash=sha256(js_source.read_bytes()).hexdigest(),
        ),
        encoding="utf-8",
    )
    (specs / "conventions-gates.yaml").write_text(
        AST_GATES_TEMPLATE.format(
            constitution_hash=sha256(constitution.read_bytes()).hexdigest(),
            mode=mode,
        ),
        encoding="utf-8",
    )
    return tmp_path, source


def test_ast_off_mode_skips_backend_and_has_no_receipt_effect(tmp_path: Path) -> None:
    project_root, source = _write_v2_project(tmp_path, "off")
    gates = load_conventions_gates(project_root)
    backend = FakeAstBackend(matches=[AstMatch("ts.no_as_any", source, 1, "as any")])

    result = run_ast_conventions(project_root, gates, source_files=[source], backend=backend)

    assert backend.scan_calls == 0
    assert result.summary is None
    assert result.violations == []
    assert result.blockers == []


def test_ast_observe_records_matches_without_ast_violations(tmp_path: Path) -> None:
    project_root, source = _write_v2_project(tmp_path, "observe")
    gates = load_conventions_gates(project_root)
    backend = FakeAstBackend(matches=[AstMatch("ts.no_as_any", source, 1, "as any")])

    result = run_ast_conventions(project_root, gates, source_files=[source], backend=backend)

    assert result.summary is not None
    assert result.summary["ast_mode"] == "observe"
    assert result.summary["ast_would_fail_count"] == 1
    assert result.violations == []
    assert result.blockers == []


def test_ast_enforce_converts_matches_to_ast_violations(tmp_path: Path) -> None:
    project_root, source = _write_v2_project(tmp_path, "enforce")
    gates = load_conventions_gates(project_root)
    backend = FakeAstBackend(matches=[AstMatch("ts.no_as_any", source, 1, "as any")])

    result = run_ast_conventions(project_root, gates, source_files=[source], backend=backend)

    assert [violation.source for violation in result.violations] == ["ast"]
    assert result.summary is not None
    assert result.summary["ast_mode"] == "enforce"
    assert result.summary["ast_would_fail_count"] == 1


def test_ast_justification_suppresses_adjacent_rule_match(tmp_path: Path) -> None:
    project_root, source = _write_v2_project(tmp_path, "enforce")
    source.write_text(
        "// livespec-justify ts.no_as_any: third-party input adapter\n"
        "const value = input as any;\n",
        encoding="utf-8",
    )
    gates = load_conventions_gates(project_root)
    backend = FakeAstBackend(matches=[AstMatch("ts.no_as_any", source, 2, "as any")])

    result = run_ast_conventions(project_root, gates, source_files=[source], backend=backend)

    assert result.summary is not None
    assert result.summary["ast_would_fail_count"] == 0
    assert result.violations == []


def test_ast_backend_absence_is_observe_warning_and_enforce_blocker(tmp_path: Path) -> None:
    observe_root, observe_source = _write_v2_project(tmp_path / "observe", "observe")
    observe_result = run_ast_conventions(
        observe_root,
        load_conventions_gates(observe_root),
        source_files=[observe_source],
        backend=FakeAstBackend(available=False),
    )
    assert observe_result.summary is not None
    assert observe_result.summary["ast_backend"]["status"] == "unavailable"
    assert observe_result.blockers == []

    enforce_root, enforce_source = _write_v2_project(tmp_path / "enforce", "enforce")
    enforce_result = run_ast_conventions(
        enforce_root,
        load_conventions_gates(enforce_root),
        source_files=[enforce_source],
        backend=FakeAstBackend(available=False),
    )
    assert enforce_result.blockers
    assert enforce_result.blockers[0].code == "ast_backend_unavailable"
