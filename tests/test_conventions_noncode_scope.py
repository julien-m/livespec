"""Regression coverage for non-code feature conventions scopes."""

import json
from pathlib import Path

import pytest

from tests._conventions_verify_scope_01 import (
    FEATURE,
    _commit_all,
    _invoke_verify,
    _write_empty_gates,
    _write_feature_scope,
)
from tests.test_goal_contracts import _write_conventions
from validator.conventions_feature_scope import FeatureScopeError, resolve_feature_scope
from validator.conventions_receipt import verify_conventions_receipt


def test_cli_verify_ci_only_scope_writes_receipt(tmp_path: Path) -> None:
    """Mapped workflows and docs constitute a feature scope."""
    _write_conventions(tmp_path, tmp_path / "ai")
    _write_empty_gates(tmp_path)
    paths = [".github/workflows/ci.yaml", "README.md"]
    for rel in paths:
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("name: CI\n" if rel.endswith("yaml") else "# CI\n")
    _write_feature_scope(tmp_path, FEATURE, paths)
    result = _invoke_verify(tmp_path, FEATURE, "ci-only")
    assert result.exit_code == 0, result.output
    assert resolve_feature_scope(tmp_path, FEATURE).paths == frozenset(paths)
    payload = json.loads(result.output)
    assert (
        verify_conventions_receipt(
            tmp_path / payload["receipt_path"],
            project_root=tmp_path,
            expected_feature_slug=FEATURE,
        ).verdict
        == "PASS"
    )


@pytest.mark.parametrize("rel", ["ci.yml", "README.md", "settings.json", "pyproject.toml"])
def test_scope_includes_mapped_config_docs_and_source(tmp_path: Path, rel: str) -> None:
    (tmp_path / rel).write_text("value\n")
    (tmp_path / "app.py").write_text("pass\n")
    _write_feature_scope(tmp_path, FEATURE, [rel, "app.py"])
    assert resolve_feature_scope(tmp_path, FEATURE).paths == frozenset({rel, "app.py"})


def test_noncode_scope_preserves_project_boundary(tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside.yaml"
    outside.write_text("name: outside\n")
    (tmp_path / "escape.yaml").symlink_to(outside)
    _write_feature_scope(
        tmp_path,
        FEATURE,
        ["escape.yaml", "missing.yaml", ".specs/features/" + FEATURE + "/implementation.md"],
    )
    with pytest.raises(FeatureScopeError, match="no mapped"):
        resolve_feature_scope(tmp_path, FEATURE)


def test_noncode_dirty_scope_requires_feature_change(tmp_path: Path) -> None:
    (tmp_path / "tracked.md").write_text("# Existing\n")
    _commit_all(tmp_path)
    (tmp_path / "ci.yaml").write_text("name: CI\n")
    feature_dir = tmp_path / ".specs/features" / FEATURE
    feature_dir.mkdir(parents=True)
    with pytest.raises(FeatureScopeError, match="missing implementation"):
        resolve_feature_scope(tmp_path, FEATURE)
    (feature_dir / "spec.md").write_text("# Feature\n")
    (tmp_path / "README.md").symlink_to(feature_dir / "spec.md")
    assert resolve_feature_scope(tmp_path, FEATURE).paths == frozenset({"ci.yaml"})


def test_ci_only_scope_keeps_linter_failures_blocking(tmp_path: Path) -> None:
    _write_conventions(tmp_path, tmp_path / "ai")
    gates = _write_empty_gates(tmp_path)
    (tmp_path / "ci.yaml").write_text("name: CI\n")
    _write_feature_scope(tmp_path, FEATURE, ["ci.yaml"])
    # Declared linters emit diagnostics for owned and unrelated files.
    command = "python3 -c 'import json; print(json.dumps(["
    command += '{"filename":"ci.yaml","code":"CI001","location":{"row":1},"message":"owned"},'
    command += '{"filename":"other.yaml","code":"CI002","location":{"row":1},"message":"unrelated"}'
    command += "]))'"
    import yaml

    data = yaml.safe_load(gates.read_text())
    data["commands"] = {"lint": [{"id": "ci-lint", "run": command}]}
    gates.write_text(yaml.safe_dump(data))
    result = _invoke_verify(tmp_path, FEATURE, "ci-fail")
    assert result.exit_code == 1, result.output
    payload = json.loads(result.output)
    assert {item["path"] for item in payload["violations"]} == {"ci.yaml"}
    assert (
        verify_conventions_receipt(
            tmp_path / payload["receipt_path"],
            project_root=tmp_path,
            expected_feature_slug=FEATURE,
        ).verdict
        == "FAIL"
    )
