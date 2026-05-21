"""Tests for root Penflow UI contract workspace helpers."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from validator.cli import app
from validator.penflow_contract import (
    bootstrap_penflow_workspace,
    get_penflow_contract_status,
)

RUNNER = CliRunner()


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_status_reports_absent_workspace(tmp_path: Path) -> None:
    status = get_penflow_contract_status(tmp_path)

    assert status.state == "absent"
    assert status.runtime_comparison == "ABSENT"
    assert status.runtime_reason == "workspace_absent"
    assert status.workspace == tmp_path / "penflow"
    assert "semantic-ui-tree.json" in status.missing
    assert status.flow_count == 0
    assert status.screen_count == 0


def test_status_extracts_semantic_tree_counts(tmp_path: Path) -> None:
    _write_json(
        tmp_path / "penflow" / "semantic-ui-tree.json",
        {
            "kind": "semantic-ui-tree",
            "flows": [{"id": "checkout"}],
            "screens": [{"id": "checkout-form"}],
        },
    )
    _write_json(tmp_path / "penflow" / "expected-ui-tree.json", {"screens": []})
    _write_json(tmp_path / "penflow" / "code-ir.json", {"flows": []})

    status = get_penflow_contract_status(tmp_path)

    assert status.state == "ready"
    assert status.flow_count == 1
    assert status.screen_count == 1
    assert status.missing == []


def test_status_blocks_missing_actual_only_when_runtime_required(
    tmp_path: Path,
) -> None:
    _write_json(tmp_path / "penflow" / "semantic-ui-tree.json", {"flows": [], "screens": []})
    _write_json(tmp_path / "penflow" / "expected-ui-tree.json", {"screens": []})
    _write_json(tmp_path / "penflow" / "code-ir.json", {"flows": []})

    non_runtime_status = get_penflow_contract_status(tmp_path)
    runtime_status = get_penflow_contract_status(tmp_path, require_actual=True)

    assert non_runtime_status.state == "ready"
    assert non_runtime_status.runtime_comparison == "ABSENT"
    assert non_runtime_status.runtime_reason == "actual_tree_not_required"
    assert runtime_status.state == "ready"
    assert runtime_status.runtime_comparison == "BLOCKED"
    assert runtime_status.runtime_reason == "actual_tree_missing"


def test_status_reports_runtime_ready_when_actual_tree_exists(tmp_path: Path) -> None:
    _write_json(tmp_path / "penflow" / "semantic-ui-tree.json", {"flows": [], "screens": []})
    _write_json(tmp_path / "penflow" / "expected-ui-tree.json", {"screens": []})
    _write_json(tmp_path / "penflow" / "code-ir.json", {"flows": []})
    _write_json(tmp_path / "penflow" / "actual-ui-tree.json", {"screens": []})

    status = get_penflow_contract_status(tmp_path, require_actual=True)

    assert status.runtime_comparison == "READY"
    assert status.runtime_reason == "actual_tree_present"


def test_status_reports_incomplete_workspace(tmp_path: Path) -> None:
    (tmp_path / "penflow").mkdir()

    status = get_penflow_contract_status(tmp_path)

    assert status.state == "incomplete"
    assert status.runtime_comparison == "BLOCKED"
    assert status.runtime_reason == "required_contract_artifacts_missing"
    assert set(status.missing) == {
        "semantic-ui-tree.json",
        "expected-ui-tree.json",
        "code-ir.json",
    }


def test_status_blocks_malformed_required_json(tmp_path: Path) -> None:
    _write_json(tmp_path / "penflow" / "semantic-ui-tree.json", {"flows": [], "screens": []})
    _write_json(tmp_path / "penflow" / "code-ir.json", {"flows": []})
    expected_tree = tmp_path / "penflow" / "expected-ui-tree.json"
    expected_tree.write_text("{not json", encoding="utf-8")

    status = get_penflow_contract_status(tmp_path)

    assert status.state == "incomplete"
    assert status.runtime_comparison == "BLOCKED"
    assert "expected-ui-tree.json" in status.missing


def test_bootstrap_copies_brainstorm_penflow_without_overwriting(tmp_path: Path) -> None:
    _write_json(
        tmp_path / ".brainstorm" / "penflow" / "semantic-ui-tree.json",
        {"flows": [{"id": "onboarding"}], "screens": []},
    )

    result = bootstrap_penflow_workspace(tmp_path)

    assert result.copied is True
    assert (tmp_path / "penflow" / "semantic-ui-tree.json").exists()

    second = bootstrap_penflow_workspace(tmp_path)

    assert second.copied is False
    assert second.reason == "workspace_exists"


def test_penflow_contract_status_cli_json(tmp_path: Path) -> None:
    _write_json(tmp_path / "penflow" / "semantic-ui-tree.json", {"flows": [], "screens": []})
    _write_json(tmp_path / "penflow" / "expected-ui-tree.json", {"screens": []})
    _write_json(tmp_path / "penflow" / "code-ir.json", {"flows": []})

    result = RUNNER.invoke(
        app,
        ["penflow-contract", "status", "--project", str(tmp_path), "--json"],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["state"] == "ready"
    assert payload["verdict"] == "PASS"
    assert payload["workspace"].endswith("penflow")


def test_penflow_contract_status_cli_text_reports_verdict(tmp_path: Path) -> None:
    _write_json(tmp_path / "penflow" / "semantic-ui-tree.json", {"flows": [], "screens": []})
    _write_json(tmp_path / "penflow" / "expected-ui-tree.json", {"screens": []})
    _write_json(tmp_path / "penflow" / "code-ir.json", {"flows": []})

    result = RUNNER.invoke(
        app,
        ["penflow-contract", "status", "--project", str(tmp_path)],
    )

    assert result.exit_code == 0, result.output
    assert "Penflow Contract Verdict: PASS" in result.output


def test_penflow_contract_status_cli_blocks_required_actual_tree(
    tmp_path: Path,
) -> None:
    _write_json(tmp_path / "penflow" / "semantic-ui-tree.json", {"flows": [], "screens": []})
    _write_json(tmp_path / "penflow" / "expected-ui-tree.json", {"screens": []})
    _write_json(tmp_path / "penflow" / "code-ir.json", {"flows": []})

    result = RUNNER.invoke(
        app,
        [
            "penflow-contract",
            "status",
            "--project",
            str(tmp_path),
            "--require-actual",
            "--json",
        ],
    )

    assert result.exit_code == 2, result.output
    payload = json.loads(result.output)
    assert payload["runtime_comparison"] == "BLOCKED"
    assert payload["runtime_reason"] == "actual_tree_missing"
    assert payload["verdict"] == "BLOCKED"
