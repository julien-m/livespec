"""Multilang infra regression tests: adapters, scope suffixes, default enforce.

These tests protect the *infrastructure-before-rules* invariant (Phase 2): if a
Rust/Kotlin file is not collected or not given the right language, every AST rule
for that language silently passes (false PASS FP2). They encode WHY each piece
matters, not just that a function returns a value.
"""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path

from validator.conventions_feature_scope import SOURCE_SUFFIXES
from validator.conventions_gates import (
    DEFAULT_AST_CATALOGS,
    ConventionsGatesV2,
    generate_conventions_gates,
    load_conventions_gates,
)
from validator.conventions_lang import adapter_for_path


def test_rust_and_kotlin_suffixes_are_collected() -> None:
    # WHY: a language whose suffix is not in scope is never scanned -> false PASS.
    for suffix in (".rs", ".kt", ".kts"):
        assert suffix in SOURCE_SUFFIXES


def test_rust_adapter_reports_rust_language() -> None:
    # WHY: the ast-grep backend only scans sources whose language matches the rule.
    assert adapter_for_path(Path("src/lib.rs")).language == "rust"


def test_kotlin_adapter_reports_kotlin_language() -> None:
    assert adapter_for_path(Path("src/Main.kt")).language == "kotlin"
    assert adapter_for_path(Path("build.gradle.kts")).language == "kotlin"


def test_rust_adapter_detects_functions_and_allow_suppression() -> None:
    # WHY: heuristics must be honest — public/private and suppression must be found.
    text = "/// doc\npub fn run() {\n    #[allow(dead_code)]\n    let _ = 1;\n}\n"
    analysis = adapter_for_path(Path("x.rs")).analyze(Path("x.rs"), text)
    assert [fn.name for fn in analysis.functions] == ["run"]
    assert analysis.functions[0].is_public is True
    assert analysis.functions[0].has_doc is True
    assert [s.token for s in analysis.suppressions] == ["allow"]


def test_kotlin_adapter_detects_functions_and_suppress() -> None:
    text = "import a.b.C\n@Suppress(\"UNCHECKED_CAST\")\nfun run() {\n    val x = 1\n}\n"
    analysis = adapter_for_path(Path("X.kt")).analyze(Path("X.kt"), text)
    assert [fn.name for fn in analysis.functions] == ["run"]
    assert [s.token for s in analysis.suppressions] == ["Suppress"]
    assert [i.module for i in analysis.imports] == ["a.b.C"]


def _write_min_project(tmp_path: Path) -> Path:
    specs = tmp_path / ".specs"
    (specs / "stacks").mkdir(parents=True)
    (specs / "constitution.md").write_text("# Constitution\n", encoding="utf-8")
    (specs / "stacks" / "_default.md").write_text(
        "# Stack\nRust and TypeScript\n", encoding="utf-8"
    )
    return tmp_path


def test_gates_init_without_flag_writes_v2_enforce(tmp_path: Path) -> None:
    # WHY (D1): the user requires enforce-by-default; no flag must NOT yield legacy v1.
    path = generate_conventions_gates(_write_min_project(tmp_path))
    gates = load_conventions_gates(path)
    assert isinstance(gates, ConventionsGatesV2)
    assert gates.schema_version == 2
    assert gates.ast_rules.mode == "enforce"
    # The multilang catalogs ship by default.
    assert tuple(gates.ast_rules.catalogs) == DEFAULT_AST_CATALOGS


def test_gates_init_ast_mode_off_opts_out_to_legacy_v1(tmp_path: Path) -> None:
    # WHY: opt-out must remain available for repos that cannot run ast-grep.
    path = generate_conventions_gates(_write_min_project(tmp_path), ast_mode="off")
    gates = load_conventions_gates(path)
    assert gates.schema_version == 1


def test_gates_init_ast_mode_observe_is_non_blocking_v2(tmp_path: Path) -> None:
    path = generate_conventions_gates(_write_min_project(tmp_path), ast_mode="observe")
    gates = load_conventions_gates(path)
    assert isinstance(gates, ConventionsGatesV2)
    assert gates.ast_rules.mode == "observe"


def test_legacy_v1_gates_still_load(tmp_path: Path) -> None:
    # WHY (compat 072 / R7): pre-existing v1 gate files must keep loading unchanged.
    specs = tmp_path / ".specs"
    specs.mkdir()
    constitution = specs / "constitution.md"
    constitution.write_text("# Constitution\n", encoding="utf-8")
    (specs / "conventions-gates.yaml").write_text(
        f"""\
schema_version: 1
generated_from:
  constitution: .specs/constitution.md
  constitution_sha256: {sha256(constitution.read_bytes()).hexdigest()}
  stack: .specs/stacks/_default.md
commands: {{lint: []}}
builtin: {{}}
coverage: {{}}
exclusions: [".specs/**"]
scope: repo
""",
        encoding="utf-8",
    )
    gates = load_conventions_gates(specs / "conventions-gates.yaml")
    assert gates.schema_version == 1
