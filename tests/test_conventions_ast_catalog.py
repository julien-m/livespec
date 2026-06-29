"""Tests for traceable AST rule catalogue validation."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path

import pytest

from validator.conventions_ast.catalog import AstCatalogError, load_ast_catalog


def _write_catalog(tmp_path: Path, *, decidability: str = "ast", precision: str = "high") -> Path:
    pass_fixture = tmp_path / "tests" / "fixtures" / "pass.ts"
    fail_fixture = tmp_path / "tests" / "fixtures" / "fail.ts"
    pass_fixture.parent.mkdir(parents=True)
    pass_fixture.write_text("const value = input as unknown;\n", encoding="utf-8")
    fail_fixture.write_text("const value = input as any;\n", encoding="utf-8")
    source_path = tmp_path / "ai-ressources" / "code-conventions" / "javascript.md"
    source_path.parent.mkdir(parents=True)
    source_path.write_text("# TypeScript Specifics\n\nany is forbidden.\n", encoding="utf-8")
    catalog = tmp_path / "ast_high.yaml"
    catalog.write_text(
        f"""\
rules:
  - id: ts.no_as_any
    title: No as any
    language: typescript
    decidability: {decidability}
    precision: {precision}
    severity: error
    source_path: {source_path}
    source_anchor: "#typescript-specifics"
    source_hash: sha256:{sha256(source_path.read_bytes()).hexdigest()}
    backend: ast-grep
    patterns:
      - kind: sg_yaml
        value: "rule: {{ pattern: '$A as any' }}"
    fixtures:
      pass: tests/fixtures/pass.ts
      fail: tests/fixtures/fail.ts
""",
        encoding="utf-8",
    )
    return catalog


def test_load_ast_catalog_accepts_high_precision_ast_rule_with_traceability(
    tmp_path: Path,
) -> None:
    catalog = load_ast_catalog(_write_catalog(tmp_path), project_root=tmp_path)

    assert [rule.id for rule in catalog.rules] == ["ts.no_as_any"]
    assert catalog.rules[0].decidability == "ast"
    assert catalog.rules[0].precision == "high"


@pytest.mark.parametrize(
    ("decidability", "precision"),
    [("semantic", "high"), ("ast", "medium"), ("graph", "low")],
)
def test_load_ast_catalog_rejects_inactive_v1_categories(
    tmp_path: Path,
    decidability: str,
    precision: str,
) -> None:
    catalog_path = _write_catalog(tmp_path, decidability=decidability, precision=precision)

    with pytest.raises(AstCatalogError, match="active v1 AST catalog"):
        load_ast_catalog(catalog_path, project_root=tmp_path)


def test_load_ast_catalog_rejects_missing_fixture(tmp_path: Path) -> None:
    catalog_path = _write_catalog(tmp_path)
    (tmp_path / "tests" / "fixtures" / "fail.ts").unlink()

    with pytest.raises(AstCatalogError, match="fixture"):
        load_ast_catalog(catalog_path, project_root=tmp_path)


def test_load_ast_catalog_rejects_missing_traceability_source(tmp_path: Path) -> None:
    catalog_path = _write_catalog(tmp_path)
    (tmp_path / "ai-ressources" / "code-conventions" / "javascript.md").unlink()

    with pytest.raises(AstCatalogError, match="source_path missing"):
        load_ast_catalog(catalog_path, project_root=tmp_path)
