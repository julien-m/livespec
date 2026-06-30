"""Real ast-grep backend proof for every active multilang rule.

WHY: a structural pattern that does not actually match its FAIL fixture (or that
matches its PASS fixture) is a silently broken rule (FP3/FP7). The fake backend
cannot catch that. These tests run the *real* ``sg`` binary; when ``sg`` is
absent they skip explicitly (justified) rather than fake a PASS.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from validator.conventions_ast.backends.ast_grep import AstGrepBackend
from validator.conventions_ast.catalog import load_ast_catalogs
from validator.conventions_ast.models import (
    AstDeterministicTestEvidence,
    AstFixtures,
    AstJustification,
    AstPattern,
    AstRule,
    AstSourceFile,
)
from validator.conventions_gates import DEFAULT_AST_CATALOGS

PROJECT_ROOT = Path(__file__).resolve().parents[1]
_SG_MISSING = shutil.which("sg") is None
skip_no_sg = pytest.mark.skipif(_SG_MISSING, reason="ast-grep (sg) binary not installed")


def _all_rules() -> list[AstRule]:
    catalogs = load_ast_catalogs(list(DEFAULT_AST_CATALOGS), project_root=PROJECT_ROOT)
    return [rule for catalog in catalogs for rule in catalog.rules]


def _source(path: Path, language: str) -> AstSourceFile:
    return AstSourceFile(path=path, language=language, text=path.read_text(encoding="utf-8"))


_RULES = _all_rules()
_RULE_IDS = [rule.id for rule in _RULES]


@skip_no_sg
@pytest.mark.parametrize("rule", _RULES, ids=_RULE_IDS)
def test_real_backend_flags_fail_fixture(rule: AstRule) -> None:
    # WHY: the FAIL fixture is the canonical violation; enforce MUST see it.
    fail_path = PROJECT_ROOT / rule.fixtures.fail_path
    backend = AstGrepBackend()
    result = backend.scan(rules=(rule,), source_files=(_source(fail_path, rule.language),))
    assert result.info.status == "available"
    assert len(result.matches) >= 1, f"{rule.id} did not flag its FAIL fixture"


@skip_no_sg
@pytest.mark.parametrize("rule", _RULES, ids=_RULE_IDS)
def test_real_backend_passes_pass_fixture(rule: AstRule) -> None:
    # WHY: the PASS fixture is conformant; a match here is a false positive.
    pass_path = PROJECT_ROOT / rule.fixtures.pass_path
    backend = AstGrepBackend()
    result = backend.scan(rules=(rule,), source_files=(_source(pass_path, rule.language),))
    assert result.info.status == "available"
    assert len(result.matches) == 0, f"{rule.id} false-positived its PASS fixture"


@skip_no_sg
def test_backend_matches_via_any_of_multiple_patterns(tmp_path: Path) -> None:
    # WHY (G6): a rule may carry several patterns; a match via ANY must be reported,
    # not only via patterns[0]. Pattern 1 cannot match; pattern 2 must.
    source = tmp_path / "x.rs"
    source.write_text("fn run() {\n    let x: Option<i32> = Some(1);\n    let _ = x.unwrap();\n}\n")
    rule = AstRule(
        id="rust.multi",
        title="multi-pattern probe",
        language="rust",
        domain="code",
        decision_kind="executable",
        decidability="ast",
        precision="high",
        severity="error",
        source_path="ai-ressources/code-conventions/rust.md",
        source_anchor="#type-system",
        source_hash="sha256:" + "0" * 64,
        backend="ast-grep",
        detector="rust.multi",
        patterns=(
            AstPattern(
                kind="sg_yaml",
                value="id: a\nlanguage: Rust\nrule:\n  pattern: $X.expect($M)\n",
            ),
            AstPattern(
                kind="sg_yaml",
                value="id: b\nlanguage: Rust\nrule:\n  pattern: $X.unwrap()\n",
            ),
        ),
        fixtures=AstFixtures(pass_path="p", fail_path="f"),
        deterministic_test_evidence=(
            AstDeterministicTestEvidence(
                test="tests/test_conventions_ast_multilang.py",
                pass_fixture="p",
                fail_fixture="f",
            ),
        ),
        justification=AstJustification(),
    )
    backend = AstGrepBackend()
    result = backend.scan(rules=(rule,), source_files=(_source(source, "rust"),))
    assert result.info.status == "available"
    assert len(result.matches) == 1


def test_all_languages_have_at_least_one_active_rule() -> None:
    # WHY: proves the multilang catalog is wired (no empty language -> no false PASS).
    languages = {rule.language for rule in _RULES}
    assert {"typescript", "rust", "swift", "kotlin"} <= languages
