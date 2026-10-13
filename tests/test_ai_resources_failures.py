# @spec FR-005: Consumers keep their reaction and carry the explicit message
#   .specs/features/085-localiser-ai-ressources-sans-chemin-en-dur/spec.md#fr-005

"""Consumer reactions when no ai-ressources root resolves (feature 085, AC-006).

Each test removes ``AIRESOURCES`` and builds a project whose manifest records a
nonexistent ``missing-corpus``; every consumer must keep its existing reaction while
surfacing the Resolution error message, and invent no fallback.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from tests.ai_resources_fixture import write_catalog, write_corpus, write_project, write_rulebook
from tests.test_init_profile import hybrid
from validator import init_from_code
from validator.cli import app
from validator.coherence.graph_builder import SpecGraph
from validator.coherence.rules.r7_conventions_gates import R7_3_ConventionsRulebookSourcesStale
from validator.coherence.violation import Severity
from validator.conventions_ast.catalog import AstCatalogError, load_ast_catalog
from validator.conventions_ast.corpus import build_corpus_manifest
from validator.conventions_ast.source_decisions import (
    build_rule_decision_manifest,
    validate_rule_decision_manifest,
)
from validator.init_recovery import conventions_are_valid

FIX = (
    "Run ./setup.sh from your ai-ressources clone, "
    "or export AIRESOURCES=<absolute path of the clone>."
)
runner = CliRunner()


@pytest.fixture
def unresolved(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Project recording a nonexistent corpus, with ``AIRESOURCES`` removed."""
    monkeypatch.delenv("AIRESOURCES", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path / "empty-home"))
    project = write_project(tmp_path / "project", manifest_path=str(tmp_path / "missing-corpus"))
    hybrid(project)
    return project


def _expected_message(project: Path) -> str:
    missing = (project.parent / "missing-corpus").resolve()
    return (
        f"ai-ressources root not resolved for project {project}: AIRESOURCES is not set; "
        f"rejected recorded paths: {missing} (from .conventions/manifest.yaml). {FIX}"
    )


def _fail_provider(*_args: object, **_kwargs: object) -> str:
    raise AssertionError("provider called before sources resolved")


def test_compile_text_reports_rulebook_error_exit_2(
    unresolved: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("validator.conventions_rules.llm_provider.call_llm", _fail_provider)

    result = runner.invoke(app, ["conventions", "compile", "--repo", str(unresolved), "--force"])

    assert result.exit_code == 2
    assert f"BLOCKED: rulebook_error: {_expected_message(unresolved)}" in result.output


def test_compile_json_reports_rulebook_error_exit_2(
    unresolved: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("validator.conventions_rules.llm_provider.call_llm", _fail_provider)

    result = runner.invoke(
        app, ["conventions", "compile", "--repo", str(unresolved), "--force", "--json"]
    )

    assert result.exit_code == 2
    payload = json.loads(result.stdout)
    assert payload == {
        "verdict": "BLOCKED",
        "reason": "rulebook_error",
        "blockers": [_expected_message(unresolved)],
    }


def test_ast_catalog_raises_catalog_error_with_message(unresolved: Path, tmp_path: Path) -> None:
    catalog = write_catalog(unresolved, write_corpus(tmp_path / "unused-corpus", "unused"))

    with pytest.raises(AstCatalogError) as caught:
        load_ast_catalog(catalog, project_root=unresolved)

    assert str(caught.value) == _expected_message(unresolved)


def test_corpus_manifest_is_empty_with_resolution_error(unresolved: Path) -> None:
    manifest = build_corpus_manifest(unresolved)

    assert manifest["ai_resources_root"] == ""
    assert manifest.get("resolution_error") == _expected_message(unresolved)
    assert manifest["total_source_count"] == 0
    assert manifest["sources"] == [] and manifest["excluded_sources"] == []


def test_rule_decisions_are_zero_with_resolution_error(unresolved: Path) -> None:
    manifest = build_rule_decision_manifest(unresolved)

    assert manifest["decisions"] == [] and manifest["excluded_sources"] == []
    assert manifest["total_source_count"] == 0
    assert manifest.get("resolution_error") == _expected_message(unresolved)
    assert any(_expected_message(unresolved) in error for error in manifest["catalog_load_errors"])
    assert any(
        blocker.startswith("catalog_load_error:")
        for blocker in validate_rule_decision_manifest(manifest)
    )


def test_r7_3_silent_without_rulebook(unresolved: Path) -> None:
    rule = R7_3_ConventionsRulebookSourcesStale()

    assert rule.check(SpecGraph(), unresolved / ".specs") == []


def test_r7_3_reports_one_explicit_error_with_rulebook(unresolved: Path, tmp_path: Path) -> None:
    write_rulebook(unresolved, write_corpus(tmp_path / "unused-corpus", "unused"))

    violations = R7_3_ConventionsRulebookSourcesStale().check(SpecGraph(), unresolved / ".specs")

    assert len(violations) == 1
    assert violations[0].severity == Severity.ERROR
    assert violations[0].message == (
        f"conventions rulebook sources cannot be verified: {_expected_message(unresolved)}"
    )


def test_conventions_validity_is_false(unresolved: Path) -> None:
    assert conventions_are_valid(unresolved) is False


def _tree(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


@pytest.mark.parametrize(
    "flags", [["--dry-run"], ["--force"], []], ids=["dry-run", "force", "plain"]
)
def test_init_from_code_prints_error_exits_2_and_writes_nothing(
    unresolved: Path, capsys: pytest.CaptureFixture[str], flags: list[str]
) -> None:
    before = _tree(unresolved)

    status = init_from_code.main(["--dir", str(unresolved), "--timeout-seconds", "30", *flags])

    assert status == 2
    assert f"ERROR: {_expected_message(unresolved)}" in capsys.readouterr().err
    assert _tree(unresolved) == before
