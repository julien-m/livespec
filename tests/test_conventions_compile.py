# @spec(AC-001)
# @spec(AC-003)
# @spec(AC-004)
# @spec(AC-005)
# @spec(AC-006)
# @spec(AC-007)
# @spec(AC-008)
# @spec(AC-019)
# @spec(AC-020)

# LiveSpec traceability anchors
# @spec(FR-001)
# @spec(FR-002)
# @spec(FR-003)
# @spec(FR-004)
# @spec(FR-009)
# @spec(FR-010)

"""Tests for compiling self-contained conventions rulebooks."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from validator.cli import app
from validator.conventions_rules import (
    _RULEBOOK_SCHEMA,
    RulebookStaleError,
    compile_conventions_rulebook,
    load_conventions_rules,
)
from validator.llm_provider import LLMProviderNotConfigured

runner = CliRunner()


def _write_conventions_project(tmp_path: Path) -> Path:
    resources = tmp_path / "ai-ressources"
    code_dir = resources / "code-conventions"
    code_dir.mkdir(parents=True)
    (code_dir / "general.md").write_text(
        "# General\n\n- Public functions must have docstrings.\n",
        encoding="utf-8",
    )
    (code_dir / "python.md").write_text(
        "# Python\n\n- Use Pydantic for external schemas.\n",
        encoding="utf-8",
    )
    conventions = tmp_path / ".conventions"
    conventions.mkdir()
    (conventions / "index.md").write_text(
        f"# Conventions\n\n> `$AIRESOURCES` = `{resources}`\n\n"
        "## code [code, tests]\n"
        "-> $AIRESOURCES/code-conventions/general.md, python.md\n",
        encoding="utf-8",
    )
    (tmp_path / ".specs").mkdir()
    return tmp_path


def _provider_payload() -> str:
    return json.dumps(
        {
            "rules": [
                {
                    "id": "code-docs",
                    "domain": "code-semantic",
                    "description": "Public functions document side effects.",
                    "check": "Flag public functions missing side-effect documentation.",
                    "source_excerpt": "Public functions must have docstrings.",
                    "blocking": True,
                    "source_paths": ["$AIRESOURCES/code-conventions/general.md"],
                }
            ],
            "unenforceable": [
                {
                    "id": "tone-polish",
                    "domain": "design-anatomy",
                    "reason": "Requires human taste judgment.",
                    "source_path": "$AIRESOURCES/code-conventions/general.md",
                }
            ],
            "waivers": [
                {
                    "rule_id": "code-docs",
                    "reason": "Legacy migration window.",
                    "expires": "2026-12-31",
                    "path_glob": "legacy/**",
                }
            ],
        }
    )


def test_rulebook_schema_required_lists_cover_all_properties() -> None:
    schema = _RULEBOOK_SCHEMA["schema"]
    assert isinstance(schema, dict)
    properties = schema["properties"]
    assert isinstance(properties, dict)

    for key in ("rules", "unenforceable", "waivers"):
        item_schema = properties[key]["items"]
        item_properties = set(item_schema["properties"])
        assert set(item_schema["required"]) == item_properties


def test_compile_rulebook_records_sources_and_provider_rules(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_root = _write_conventions_project(tmp_path)
    calls: list[dict[str, object]] = []

    def fake_call_llm(
        prompt: str,
        json_schema: dict[str, object] | None = None,
        model: str | None = None,
    ) -> str:
        calls.append({"prompt": prompt, "json_schema": json_schema, "model": model})
        return _provider_payload()

    monkeypatch.setattr("validator.conventions_rules.llm_provider.call_llm", fake_call_llm)

    path = compile_conventions_rulebook(project_root, force=True)
    rulebook = load_conventions_rules(path)

    assert path == project_root / ".specs" / "conventions-rulebook.yaml"
    assert len(calls) == 1
    assert "Public functions must have docstrings" in str(calls[0]["prompt"])
    assert calls[0]["json_schema"] is not None
    assert {source.path for source in rulebook.sources} == {
        "$AIRESOURCES/code-conventions/general.md",
        "$AIRESOURCES/code-conventions/python.md",
    }
    assert len(rulebook.sources[0].sha256) == 64
    assert rulebook.rules[0].id == "code-docs"
    assert rulebook.rules[0].blocking is True
    assert rulebook.waivers[0].path_glob == "legacy/**"


def test_compile_rulebook_refuses_stale_existing_hash_without_force(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_root = _write_conventions_project(tmp_path)
    monkeypatch.setattr(
        "validator.conventions_rules.llm_provider.call_llm",
        lambda *_args, **_kwargs: _provider_payload(),
    )
    path = compile_conventions_rulebook(project_root, force=True)
    original = path.read_text(encoding="utf-8")
    source = project_root / "ai-ressources" / "code-conventions" / "general.md"
    source.write_text("# General\n\n- Changed convention.\n", encoding="utf-8")

    with pytest.raises(RulebookStaleError):
        compile_conventions_rulebook(project_root, force=False)

    assert path.read_text(encoding="utf-8") == original


def test_conventions_compile_cli_writes_rulebook(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_root = _write_conventions_project(tmp_path)
    monkeypatch.setattr(
        "validator.conventions_rules.llm_provider.call_llm",
        lambda *_args, **_kwargs: _provider_payload(),
    )

    result = runner.invoke(app, ["conventions", "compile", "--repo", str(project_root), "--force"])

    assert result.exit_code == 0, result.output
    assert "conventions rulebook written" in result.output
    assert (project_root / ".specs" / "conventions-rulebook.yaml").is_file()


def test_conventions_compile_cli_json_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_root = _write_conventions_project(tmp_path)
    monkeypatch.setattr(
        "validator.conventions_rules.llm_provider.call_llm",
        lambda *_args, **_kwargs: _provider_payload(),
    )

    result = runner.invoke(
        app,
        ["conventions", "compile", "--repo", str(project_root), "--force", "--json"],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["status"] == "written"
    assert payload["path"].endswith(".specs/conventions-rulebook.yaml")


def test_conventions_compile_cli_provider_not_configured_blocks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_root = _write_conventions_project(tmp_path)

    def raise_not_configured(*_args: object, **_kwargs: object) -> str:
        raise LLMProviderNotConfigured()

    monkeypatch.setattr("validator.conventions_rules.llm_provider.call_llm", raise_not_configured)

    result = runner.invoke(
        app,
        ["conventions", "compile", "--repo", str(project_root), "--force", "--json"],
    )

    assert result.exit_code == 2, result.output
    payload = json.loads(result.output)
    assert payload["verdict"] == "BLOCKED"
    assert payload["reason"] == "provider_not_configured"
