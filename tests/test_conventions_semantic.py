# LiveSpec traceability anchors
# @spec(FR-005)
# @spec(FR-006)
# @spec(FR-007)
# @spec(FR-008)
# @spec(FR-010)

"""Tests for Layer 4 semantic conventions Engine C."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from validator.cli import app
from validator.conventions_engine_c import SemanticConventionVerdict, run_semantic_conventions
from validator.conventions_rules import ConventionsRules
from validator.llm_provider import LLMProviderNotConfigured

runner = CliRunner()


def _write_rulebook(tmp_path: Path, waiver_expires: str = "2026-12-31") -> Path:
    specs = tmp_path / ".specs"
    specs.mkdir()
    path = specs / "conventions-rulebook.yaml"
    path.write_text(
        f"""
schema_version: 1
compiled_at: "2026-06-12T00:00:00Z"
sources:
  - path: "$AIRESOURCES/code-conventions/general.md"
    sha256: "{"0" * 64}"
rules:
  - id: code-docs
    domain: code-semantic
    description: "Public functions document side effects."
    check: "Flag public functions missing side-effect documentation."
    source_excerpt: "Public functions must have docstrings."
    blocking: true
    source_paths: ["$AIRESOURCES/code-conventions/general.md"]
  - id: code-naming
    domain: code-semantic
    description: "Names are descriptive."
    check: "Flag vague function names."
    source_excerpt: "Names must be descriptive."
    blocking: false
    source_paths: ["$AIRESOURCES/code-conventions/general.md"]
  - id: design-label
    domain: design-anatomy
    description: "Labels match controls."
    check: "Flag mismatched labels."
    source_excerpt: "Labels should match controls."
    blocking: true
    source_paths: ["$AIRESOURCES/design/components/forms.md"]
unenforceable:
  - id: tone-polish
    domain: design-anatomy
    reason: "Subjective editorial quality."
waivers:
  - rule_id: code-docs
    reason: "Legacy migration window."
    expires: "{waiver_expires}"
    path_glob: "legacy/**"
""",
        encoding="utf-8",
    )
    return path


def test_engine_c_batches_one_provider_call_per_domain(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_rulebook(tmp_path)
    calls: list[str] = []

    def fake_call_llm(
        prompt: str,
        json_schema: dict[str, object] | None = None,
        model: str | None = None,
        temperature: int | None = None,
    ) -> str:
        calls.append(prompt)
        assert json_schema is not None
        assert temperature == 0
        return json.dumps({"findings": []})

    monkeypatch.setattr("validator.conventions_engine_c.llm_provider.call_llm", fake_call_llm)

    result = run_semantic_conventions(
        tmp_path,
        source_texts={"src/app.py": "def x():\n    return None\n"},
    )

    assert result.verdict is SemanticConventionVerdict.PASS
    assert result.provider_calls == 2
    assert len(calls) == 2


def test_engine_c_uses_configured_review_model_not_implementation_model(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_rulebook(tmp_path)
    config_dir = tmp_path / ".specs" / "semantic"
    config_dir.mkdir()
    (config_dir / "config.yaml").write_text("review_model: reviewer-model\n", encoding="utf-8")
    models: list[str | None] = []

    def fake_call_llm(
        _prompt: str,
        json_schema: dict[str, object] | None = None,
        model: str | None = None,
        temperature: int | None = None,
    ) -> str:
        models.append(model)
        assert json_schema is not None
        assert temperature == 0
        return json.dumps({"findings": []})

    monkeypatch.setattr("validator.conventions_engine_c.llm_provider.call_llm", fake_call_llm)

    result = run_semantic_conventions(
        tmp_path,
        source_texts={"src/app.py": "def x():\n    return None\n"},
        model="implementation-model",
    )

    assert result.verdict is SemanticConventionVerdict.PASS
    assert models == ["reviewer-model", "reviewer-model"]
    assert "implementation-model" not in models



def test_engine_c_passes_none_to_provider_when_no_review_model_is_configured(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_rulebook(tmp_path)
    models: list[str | None] = []

    def fake_call_llm(
        _prompt: str,
        json_schema: dict[str, object] | None = None,
        model: str | None = None,
        temperature: int | None = None,
    ) -> str:
        models.append(model)
        assert json_schema is not None
        assert temperature == 0
        return json.dumps({"findings": []})

    monkeypatch.setattr("validator.conventions_engine_c.llm_provider.call_llm", fake_call_llm)

    result = run_semantic_conventions(tmp_path, source_texts={"src/app.py": "def x(): pass\n"})

    assert result.verdict is SemanticConventionVerdict.PASS
    assert models == [None, None]


def test_blocking_finding_fails_and_non_blocking_is_preserved(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_rulebook(tmp_path, waiver_expires="2025-01-01")

    def fake_call_llm(prompt: str, *_args: object, **_kwargs: object) -> str:
        if "domain design-anatomy" in prompt:
            return json.dumps({"findings": []})
        return json.dumps(
            {
                "findings": [
                    {
                        "rule_id": "code-docs",
                        "path": "src/app.py",
                        "line": 3,
                        "message": "Missing side-effect documentation.",
                        "severity": "blocking",
                    },
                    {
                        "rule_id": "code-naming",
                        "path": "src/app.py",
                        "line": 1,
                        "message": "Function name is vague.",
                        "severity": "warning",
                    },
                ]
            }
        )

    monkeypatch.setattr("validator.conventions_engine_c.llm_provider.call_llm", fake_call_llm)

    result = run_semantic_conventions(tmp_path, source_texts={"src/app.py": "def x(): pass\n"})

    assert result.verdict is SemanticConventionVerdict.FAIL
    assert [finding.rule_id for finding in result.findings] == ["code-docs", "code-naming"]
    assert result.findings[0].waived is False
    assert result.findings[1].blocking is False


def test_active_waiver_suppresses_matching_blocking_finding(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_rulebook(tmp_path)

    def fake_call_llm(prompt: str, *_args: object, **_kwargs: object) -> str:
        if "domain design-anatomy" in prompt:
            return json.dumps({"findings": []})
        return json.dumps(
            {
                "findings": [
                    {
                        "rule_id": "code-docs",
                        "path": "legacy/app.py",
                        "line": 4,
                        "message": "Missing side-effect documentation.",
                        "severity": "blocking",
                    }
                ]
            }
        )

    monkeypatch.setattr("validator.conventions_engine_c.llm_provider.call_llm", fake_call_llm)

    result = run_semantic_conventions(
        tmp_path,
        source_texts={"legacy/app.py": "def old(): pass\n"},
    )

    assert result.verdict is SemanticConventionVerdict.PASS
    assert result.findings[0].waived is True


def test_provider_down_blocks_semantic_gate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_rulebook(tmp_path)

    def raise_provider_down(*_args: object, **_kwargs: object) -> str:
        raise LLMProviderNotConfigured()

    monkeypatch.setattr("validator.conventions_engine_c.llm_provider.call_llm", raise_provider_down)

    result = run_semantic_conventions(tmp_path, source_texts={"src/app.py": "def x(): pass\n"})

    assert result.verdict is SemanticConventionVerdict.BLOCKED
    assert result.blockers
    assert not result.findings


def test_invalid_provider_json_blocks_semantic_gate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_rulebook(tmp_path)
    monkeypatch.setattr(
        "validator.conventions_engine_c.llm_provider.call_llm",
        lambda *_args, **_kwargs: "{not-json",
    )

    result = run_semantic_conventions(tmp_path, source_texts={"src/app.py": "def x(): pass\n"})

    assert result.verdict is SemanticConventionVerdict.BLOCKED
    assert result.blockers


def test_unknown_provider_rule_id_blocks_semantic_gate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_rulebook(tmp_path)
    monkeypatch.setattr(
        "validator.conventions_engine_c.llm_provider.call_llm",
        lambda *_args, **_kwargs: json.dumps(
            {
                "findings": [
                    {
                        "rule_id": "unknown-rule",
                        "path": "src/app.py",
                        "line": 1,
                        "message": "Unknown.",
                        "severity": "warning",
                    }
                ]
            }
        ),
    )

    result = run_semantic_conventions(tmp_path, source_texts={"src/app.py": "def x(): pass\n"})

    assert result.verdict is SemanticConventionVerdict.BLOCKED
    assert "unknown-rule" in result.blockers[0]


def test_rulebook_schema_loads_semantic_fixture(tmp_path: Path) -> None:
    path = _write_rulebook(tmp_path)

    rulebook = ConventionsRules.load(path)

    assert len(rulebook.rules) == 3
    assert rulebook.rules[0].domain == "code-semantic"


def test_conventions_semantic_cli_json_pass(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_rulebook(tmp_path)
    monkeypatch.setattr(
        "validator.conventions_engine_c.llm_provider.call_llm",
        lambda *_args, **_kwargs: json.dumps({"findings": []}),
    )

    result = runner.invoke(app, ["conventions", "semantic", "--repo", str(tmp_path), "--json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["verdict"] == "PASS"


def test_conventions_semantic_cli_missing_rulebook_blocks(
    tmp_path: Path,
) -> None:
    (tmp_path / ".specs").mkdir()

    result = runner.invoke(app, ["conventions", "semantic", "--repo", str(tmp_path), "--json"])

    assert result.exit_code == 2, result.output
    payload = json.loads(result.output)
    assert payload["verdict"] == "BLOCKED"
    assert payload["reason"] == "rulebook_missing"
