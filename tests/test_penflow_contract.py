# LiveSpec traceability anchors
# @spec(AC-002)
# @spec(AC-010)
# @spec(AC-011)
# @spec(AC-012)
# @spec(AC-013)

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


def _write_png(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\x89PNG\r\n\x1a\n")


def _write_mockup_validation(path: Path, feature_slug: str, status: str = "PASS") -> None:
    (path / ".mockup-validation" / feature_slug).mkdir(parents=True, exist_ok=True)
    (path / ".mockup-validation" / feature_slug / "checklist.md").write_text(
        "# Checklist\n",
        encoding="utf-8",
    )
    _write_json(path / ".mockup-validation" / feature_slug / "manifest.json", {"status": status})
    _write_json(
        path / ".mockup-validation" / feature_slug / "drift-report.json",
        {"status": status},
    )
    (path / ".mockup-validation" / "audit-report.md").parent.mkdir(parents=True, exist_ok=True)
    (path / ".mockup-validation" / "audit-report.md").write_text(
        f"status: {status}\n",
        encoding="utf-8",
    )
    _write_json(
        path / ".mockup-validation" / "visual-evidence" / "manifest.json",
        {"status": status, "screens": [{"screen_id": "dashboard"}]},
    )
    (path / ".mockup-validation" / "visual-evidence" / "visual-report.md").write_text(
        f"status: {status}\n",
        encoding="utf-8",
    )
    _write_png(path / ".mockup-validation" / "visual-evidence" / "dashboard.png")


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
    (tmp_path / "penflow" / "flow-ui-contract").mkdir(parents=True)
    _write_json(
        tmp_path / "penflow" / "ui.pen",
        {"children": [{"type": "frame", "width": 1440, "height": 900}]},
    )
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
    (tmp_path / "penflow" / "flow-ui-contract").mkdir(parents=True)
    _write_json(
        tmp_path / "penflow" / "ui.pen",
        {"children": [{"type": "frame", "width": 1440, "height": 900}]},
    )
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
    (tmp_path / "penflow" / "flow-ui-contract").mkdir(parents=True)
    _write_json(
        tmp_path / "penflow" / "ui.pen",
        {"children": [{"type": "frame", "width": 1440, "height": 900}]},
    )
    _write_json(tmp_path / "penflow" / "semantic-ui-tree.json", {"flows": [], "screens": []})
    _write_json(tmp_path / "penflow" / "expected-ui-tree.json", {"screens": []})
    _write_json(tmp_path / "penflow" / "code-ir.json", {"flows": []})
    _write_json(tmp_path / "penflow" / "actual-ui-tree.json", {"screens": []})

    status = get_penflow_contract_status(tmp_path, require_actual=True)

    assert status.runtime_comparison == "READY"
    assert status.runtime_reason == "actual_tree_present"


def test_status_reports_runtime_fail_when_compare_report_fails(tmp_path: Path) -> None:
    (tmp_path / "penflow" / "flow-ui-contract").mkdir(parents=True)
    _write_json(
        tmp_path / "penflow" / "ui.pen",
        {"children": [{"type": "frame", "width": 1440, "height": 900}]},
    )
    _write_json(tmp_path / "penflow" / "semantic-ui-tree.json", {"flows": [], "screens": []})
    _write_json(tmp_path / "penflow" / "expected-ui-tree.json", {"screens": []})
    _write_json(tmp_path / "penflow" / "code-ir.json", {"flows": []})
    _write_json(tmp_path / "penflow" / "actual-ui-tree.json", {"screens": []})
    _write_json(
        tmp_path / "penflow" / "compare-report.json",
        {
            "status": "FAIL",
            "summary": {"errors": 0, "warnings": 1, "issues": 1},
            "issues": [{"code": "node.bbox.width", "severity": "warning"}],
        },
    )

    status = get_penflow_contract_status(tmp_path, require_actual=True)

    assert status.runtime_comparison == "FAIL"
    assert status.runtime_reason == "compare_report_failed"
    assert status.compare_status == "FAIL"
    assert status.compare_issue_count == 1


def test_status_reports_runtime_fail_when_compare_report_has_issues(tmp_path: Path) -> None:
    (tmp_path / "penflow" / "flow-ui-contract").mkdir(parents=True)
    _write_json(
        tmp_path / "penflow" / "ui.pen",
        {"children": [{"type": "frame", "width": 1440, "height": 900}]},
    )
    _write_json(tmp_path / "penflow" / "semantic-ui-tree.json", {"flows": [], "screens": []})
    _write_json(tmp_path / "penflow" / "expected-ui-tree.json", {"screens": []})
    _write_json(tmp_path / "penflow" / "code-ir.json", {"flows": []})
    _write_json(tmp_path / "penflow" / "actual-ui-tree.json", {"screens": []})
    _write_json(
        tmp_path / "penflow" / "compare-report.json",
        {
            "status": "PASS",
            "summary": {"errors": 0, "warnings": 1, "issues": 1},
            "issues": [{"code": "node.text", "severity": "warning"}],
        },
    )

    status = get_penflow_contract_status(tmp_path, require_actual=True)

    assert status.runtime_comparison == "FAIL"
    assert status.runtime_reason == "compare_report_has_issues"
    assert status.compare_status == "PASS"
    assert status.compare_issue_count == 1


def test_status_reports_runtime_ready_when_compare_report_passes_without_issues(
    tmp_path: Path,
) -> None:
    (tmp_path / "penflow" / "flow-ui-contract").mkdir(parents=True)
    _write_json(
        tmp_path / "penflow" / "ui.pen",
        {"children": [{"type": "frame", "width": 1440, "height": 900}]},
    )
    _write_json(tmp_path / "penflow" / "semantic-ui-tree.json", {"flows": [], "screens": []})
    _write_json(tmp_path / "penflow" / "expected-ui-tree.json", {"screens": []})
    _write_json(tmp_path / "penflow" / "code-ir.json", {"flows": []})
    _write_json(tmp_path / "penflow" / "actual-ui-tree.json", {"screens": []})
    _write_json(
        tmp_path / "penflow" / "compare-report.json",
        {"status": "PASS", "summary": {"issues": 0}, "issues": []},
    )

    status = get_penflow_contract_status(tmp_path, require_actual=True)

    assert status.runtime_comparison == "READY"
    assert status.runtime_reason == "compare_report_passed"
    assert status.compare_status == "PASS"
    assert status.compare_issue_count == 0


def test_status_reports_incomplete_workspace(tmp_path: Path) -> None:
    (tmp_path / "penflow").mkdir()

    status = get_penflow_contract_status(tmp_path)

    assert status.state == "incomplete"
    assert status.runtime_comparison == "BLOCKED"
    assert status.runtime_reason == "required_contract_artifacts_missing"
    assert set(status.missing) == {
        "flow-ui-contract/",
        "ui.pen",
        "semantic-ui-tree.json",
        "expected-ui-tree.json",
        "code-ir.json",
    }


def test_status_blocks_malformed_required_json(tmp_path: Path) -> None:
    (tmp_path / "penflow" / "flow-ui-contract").mkdir(parents=True)
    _write_json(
        tmp_path / "penflow" / "ui.pen",
        {"children": [{"type": "frame", "width": 1440, "height": 900}]},
    )
    _write_json(tmp_path / "penflow" / "semantic-ui-tree.json", {"flows": [], "screens": []})
    _write_json(tmp_path / "penflow" / "code-ir.json", {"flows": []})
    expected_tree = tmp_path / "penflow" / "expected-ui-tree.json"
    expected_tree.write_text("{not json", encoding="utf-8")

    status = get_penflow_contract_status(tmp_path)

    assert status.state == "incomplete"
    assert status.runtime_comparison == "BLOCKED"
    assert "expected-ui-tree.json" in status.missing


def test_status_requires_ui_pen_and_flow_contract_for_ready_workspace(tmp_path: Path) -> None:
    _write_json(tmp_path / "penflow" / "semantic-ui-tree.json", {"flows": [], "screens": []})
    _write_json(tmp_path / "penflow" / "expected-ui-tree.json", {"screens": []})
    _write_json(tmp_path / "penflow" / "code-ir.json", {"flows": []})

    status = get_penflow_contract_status(tmp_path)

    assert status.state == "incomplete"
    assert status.runtime_comparison == "BLOCKED"
    assert "flow-ui-contract/" in status.missing
    assert "ui.pen" in status.missing


def test_status_blocks_duplicate_pen_files_outside_canonical_workspace(tmp_path: Path) -> None:
    (tmp_path / "penflow" / "flow-ui-contract").mkdir(parents=True)
    _write_json(
        tmp_path / "penflow" / "ui.pen",
        {"children": [{"type": "frame", "width": 1440, "height": 900}]},
    )
    _write_json(tmp_path / "penflow" / "semantic-ui-tree.json", {"flows": [], "screens": []})
    _write_json(tmp_path / "penflow" / "expected-ui-tree.json", {"screens": []})
    _write_json(tmp_path / "penflow" / "code-ir.json", {"flows": []})
    _write_json(tmp_path / ".specs" / "design" / "ui.pen", {"children": []})

    status = get_penflow_contract_status(tmp_path)

    assert status.state == "incomplete"
    assert status.runtime_comparison == "BLOCKED"
    assert "duplicate_pen:.specs/design/ui.pen" in status.missing


def test_status_blocks_bad_desktop_web_mockup_quality(tmp_path: Path) -> None:
    (tmp_path / "penflow" / "flow-ui-contract").mkdir(parents=True)
    _write_json(
        tmp_path / "penflow" / "ui.pen",
        {
            "children": [
                {
                    "type": "frame",
                    "name": "Bookings",
                    "width": 390,
                    "height": 844,
                    "children": [
                        {"type": "text", "content": "ui.pageTitle"},
                        {"type": "text", "content": "appointment.clientName"},
                        {"type": "text", "content": "Escape key"},
                    ],
                }
            ]
        },
    )
    _write_json(tmp_path / "penflow" / "semantic-ui-tree.json", {"flows": [], "screens": []})
    _write_json(tmp_path / "penflow" / "expected-ui-tree.json", {"screens": []})
    _write_json(tmp_path / "penflow" / "code-ir.json", {"flows": []})

    status = get_penflow_contract_status(tmp_path, target="web-desktop")

    assert status.state == "incomplete"
    assert status.runtime_comparison == "BLOCKED"
    assert "ui.pen:desktop_frame_width" in status.missing
    assert "ui.pen:placeholder_text" in status.missing
    assert "ui.pen:fake_interaction_control" in status.missing


def test_status_ignores_internal_names_for_placeholder_text(tmp_path: Path) -> None:
    (tmp_path / "penflow" / "flow-ui-contract").mkdir(parents=True)
    _write_json(
        tmp_path / "penflow" / "ui.pen",
        {
            "children": [
                {
                    "type": "frame",
                    "name": "bookings_dashboard.screen",
                    "width": 1440,
                    "height": 900,
                    "children": [
                        {
                            "type": "text",
                            "name": "bookings_dashboard.page_title",
                            "content": "Bookings",
                        },
                        {
                            "type": "text",
                            "name": "appointment.clientName",
                            "content": "Marie Dubois",
                        },
                    ],
                }
            ]
        },
    )
    _write_json(tmp_path / "penflow" / "semantic-ui-tree.json", {"flows": [], "screens": []})
    _write_json(tmp_path / "penflow" / "expected-ui-tree.json", {"screens": []})
    _write_json(tmp_path / "penflow" / "code-ir.json", {"flows": []})

    status = get_penflow_contract_status(tmp_path, target="web-desktop")

    assert status.state == "ready"
    assert "ui.pen:placeholder_text" not in status.missing


def test_status_accepts_penflow_design_contract_screens_format(tmp_path: Path) -> None:
    (tmp_path / "penflow" / "flow-ui-contract").mkdir(parents=True)
    _write_json(
        tmp_path / "penflow" / "ui.pen",
        {
            "_format": "penflow-design-contract",
            "screens": [
                {
                    "id": "bookings-main",
                    "width": 1440,
                    "height": 900,
                    "regions": [{"type": "text", "text": "Bookings"}],
                },
                {
                    "id": "bookings-empty-state",
                    "width": 1440,
                    "height": 900,
                    "regions": [{"type": "text", "text": "No appointments"}],
                },
            ],
        },
    )
    _write_json(tmp_path / "penflow" / "semantic-ui-tree.json", {"flows": [], "screens": []})
    _write_json(tmp_path / "penflow" / "expected-ui-tree.json", {"screens": []})
    _write_json(tmp_path / "penflow" / "code-ir.json", {"flows": []})

    status = get_penflow_contract_status(tmp_path, target="web-desktop")

    assert status.state == "ready"
    assert status.missing == []


def test_status_blocks_missing_required_design_registry(tmp_path: Path) -> None:
    feature_slug = "001-booking-dashboard"
    (tmp_path / "penflow" / "flow-ui-contract").mkdir(parents=True)
    _write_json(
        tmp_path / "penflow" / "ui.pen",
        {"children": [{"type": "frame", "width": 1440, "height": 900}]},
    )
    _write_json(tmp_path / "penflow" / "semantic-ui-tree.json", {"flows": [], "screens": []})
    _write_json(tmp_path / "penflow" / "expected-ui-tree.json", {"screens": []})
    _write_json(tmp_path / "penflow" / "code-ir.json", {"flows": []})

    status = get_penflow_contract_status(
        tmp_path,
        require_design_registry=True,
        feature_slug=feature_slug,
    )

    assert status.state == "incomplete"
    assert status.runtime_comparison == "BLOCKED"
    assert status.design_registry_required is True
    assert f".specs/design/screens/{feature_slug}/" in status.design_registry_missing
    assert f".specs/design/baselines/{feature_slug}/" in status.design_registry_missing


def test_status_accepts_required_design_registry_without_design_ui_pen(tmp_path: Path) -> None:
    feature_slug = "001-booking-dashboard"
    (tmp_path / "penflow" / "flow-ui-contract").mkdir(parents=True)
    _write_json(
        tmp_path / "penflow" / "ui.pen",
        {"children": [{"type": "frame", "width": 1440, "height": 900}]},
    )
    _write_json(tmp_path / "penflow" / "semantic-ui-tree.json", {"flows": [], "screens": []})
    _write_json(tmp_path / "penflow" / "expected-ui-tree.json", {"screens": []})
    _write_json(tmp_path / "penflow" / "code-ir.json", {"flows": []})
    (tmp_path / ".specs" / "design" / "screens").mkdir(parents=True)
    (tmp_path / ".specs" / "design" / "screens" / "index.md").write_text(
        "# Screen Index\n",
        encoding="utf-8",
    )
    (tmp_path / ".specs" / "design" / "changelog.md").write_text(
        "# Changelog\n",
        encoding="utf-8",
    )
    _write_png(tmp_path / ".specs" / "design" / "screens" / feature_slug / "dashboard.png")
    (tmp_path / ".specs" / "design" / "baselines" / feature_slug).mkdir(parents=True)

    status = get_penflow_contract_status(
        tmp_path,
        require_design_registry=True,
        feature_slug=feature_slug,
    )

    assert status.state == "ready"
    assert status.design_registry_missing == []
    assert f".specs/design/screens/{feature_slug}/" not in status.missing


def test_status_blocks_missing_required_mockup_validation(tmp_path: Path) -> None:
    feature_slug = "001-booking-dashboard"
    (tmp_path / "penflow" / "flow-ui-contract").mkdir(parents=True)
    _write_json(
        tmp_path / "penflow" / "ui.pen",
        {"children": [{"type": "frame", "width": 1440, "height": 900}]},
    )
    _write_json(tmp_path / "penflow" / "semantic-ui-tree.json", {"flows": [], "screens": []})
    _write_json(tmp_path / "penflow" / "expected-ui-tree.json", {"screens": []})
    _write_json(tmp_path / "penflow" / "code-ir.json", {"flows": []})

    status = get_penflow_contract_status(
        tmp_path,
        require_mockup_validation=True,
        feature_slug=feature_slug,
    )

    assert status.state == "incomplete"
    assert status.runtime_comparison == "BLOCKED"
    assert status.mockup_validation_required is True
    assert ".mockup-validation/audit-report.md" in status.mockup_validation_missing
    assert f".mockup-validation/{feature_slug}/checklist.md" in status.mockup_validation_missing
    assert ".mockup-validation/visual-evidence/manifest.json:status" in status.missing


def test_status_accepts_required_mockup_validation(tmp_path: Path) -> None:
    feature_slug = "001-booking-dashboard"
    (tmp_path / "penflow" / "flow-ui-contract").mkdir(parents=True)
    _write_json(
        tmp_path / "penflow" / "ui.pen",
        {"children": [{"type": "frame", "width": 1440, "height": 900}]},
    )
    _write_json(tmp_path / "penflow" / "semantic-ui-tree.json", {"flows": [], "screens": []})
    _write_json(tmp_path / "penflow" / "expected-ui-tree.json", {"screens": []})
    _write_json(tmp_path / "penflow" / "code-ir.json", {"flows": []})
    _write_mockup_validation(tmp_path, feature_slug)

    status = get_penflow_contract_status(
        tmp_path,
        require_mockup_validation=True,
        feature_slug=feature_slug,
    )

    assert status.state == "ready"
    assert status.mockup_validation_status == "PASS"
    assert status.mockup_validation_missing == []


def test_status_rejects_non_pass_mockup_validation(tmp_path: Path) -> None:
    feature_slug = "001-booking-dashboard"
    (tmp_path / "penflow" / "flow-ui-contract").mkdir(parents=True)
    _write_json(
        tmp_path / "penflow" / "ui.pen",
        {"children": [{"type": "frame", "width": 1440, "height": 900}]},
    )
    _write_json(tmp_path / "penflow" / "semantic-ui-tree.json", {"flows": [], "screens": []})
    _write_json(tmp_path / "penflow" / "expected-ui-tree.json", {"screens": []})
    _write_json(tmp_path / "penflow" / "code-ir.json", {"flows": []})
    _write_mockup_validation(tmp_path, feature_slug, status="PASSED_WITH_WARNINGS")

    status = get_penflow_contract_status(
        tmp_path,
        require_mockup_validation=True,
        feature_slug=feature_slug,
    )

    assert status.state == "incomplete"
    assert status.mockup_validation_status == "PASSED_WITH_WARNINGS"
    assert ".mockup-validation/visual-evidence/manifest.json:status" in status.missing


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


def test_bootstrap_prefers_handoff_penflow_before_legacy_brainstorm(
    tmp_path: Path,
) -> None:
    _write_json(
        tmp_path / "handoff" / "penflow" / "semantic-ui-tree.json",
        {"flows": [{"id": "canonical"}], "screens": []},
    )
    _write_json(
        tmp_path / ".brainstorm" / "penflow" / "semantic-ui-tree.json",
        {"flows": [{"id": "legacy"}], "screens": []},
    )

    result = bootstrap_penflow_workspace(tmp_path)

    assert result.copied is True
    assert result.source == tmp_path / "handoff" / "penflow"
    assert json.loads(
        (tmp_path / "penflow" / "semantic-ui-tree.json").read_text(encoding="utf-8")
    ) == {"flows": [{"id": "canonical"}], "screens": []}


def test_status_ignores_handoff_penflow_source_duplicate_after_import(
    tmp_path: Path,
) -> None:
    (tmp_path / "penflow" / "flow-ui-contract").mkdir(parents=True)
    _write_json(
        tmp_path / "penflow" / "ui.pen",
        {"children": [{"type": "frame", "width": 1440, "height": 900}]},
    )
    _write_json(tmp_path / "penflow" / "semantic-ui-tree.json", {"flows": [], "screens": []})
    _write_json(tmp_path / "penflow" / "expected-ui-tree.json", {"screens": []})
    _write_json(tmp_path / "penflow" / "code-ir.json", {"flows": []})
    _write_json(
        tmp_path / "handoff" / "penflow" / "ui.pen",
        {"children": [{"type": "frame", "width": 1440, "height": 900}]},
    )

    status = get_penflow_contract_status(tmp_path)

    assert status.state == "ready"
    assert "duplicate_pen:handoff/penflow/ui.pen" not in status.missing


def test_bootstrap_imports_explicit_penflow_source_without_brainstorm_subdir(
    tmp_path: Path,
) -> None:
    source = tmp_path / "brainstorm-project" / "penflow"
    destination_project = tmp_path / "livespec-project"
    _write_json(source / "semantic-ui-tree.json", {"flows": [{"id": "onboarding"}], "screens": []})

    result = bootstrap_penflow_workspace(destination_project, source_dir=source)

    assert result.copied is True
    assert result.source == source
    assert (destination_project / "penflow" / "semantic-ui-tree.json").exists()


def test_penflow_contract_status_cli_json(tmp_path: Path) -> None:
    (tmp_path / "penflow" / "flow-ui-contract").mkdir(parents=True)
    _write_json(
        tmp_path / "penflow" / "ui.pen",
        {"children": [{"type": "frame", "width": 1440, "height": 900}]},
    )
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
    (tmp_path / "penflow" / "flow-ui-contract").mkdir(parents=True)
    _write_json(
        tmp_path / "penflow" / "ui.pen",
        {"children": [{"type": "frame", "width": 1440, "height": 900}]},
    )
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
    (tmp_path / "penflow" / "flow-ui-contract").mkdir(parents=True)
    _write_json(
        tmp_path / "penflow" / "ui.pen",
        {"children": [{"type": "frame", "width": 1440, "height": 900}]},
    )
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


def test_penflow_contract_status_cli_blocks_required_design_registry(tmp_path: Path) -> None:
    feature_slug = "001-booking-dashboard"
    (tmp_path / "penflow" / "flow-ui-contract").mkdir(parents=True)
    _write_json(
        tmp_path / "penflow" / "ui.pen",
        {"children": [{"type": "frame", "width": 1440, "height": 900}]},
    )
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
            "--require-design-registry",
            "--feature",
            feature_slug,
            "--json",
        ],
    )

    assert result.exit_code == 2, result.output
    payload = json.loads(result.output)
    assert payload["verdict"] == "BLOCKED"
    assert payload["design_registry_required"] is True
    assert f".specs/design/screens/{feature_slug}/" in payload["design_registry_missing"]


def test_penflow_contract_status_cli_blocks_required_mockup_validation(tmp_path: Path) -> None:
    feature_slug = "001-booking-dashboard"
    (tmp_path / "penflow" / "flow-ui-contract").mkdir(parents=True)
    _write_json(
        tmp_path / "penflow" / "ui.pen",
        {"children": [{"type": "frame", "width": 1440, "height": 900}]},
    )
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
            "--require-mockup-validation",
            "--feature",
            feature_slug,
            "--json",
        ],
    )

    assert result.exit_code == 2, result.output
    payload = json.loads(result.output)
    assert payload["verdict"] == "BLOCKED"
    assert payload["mockup_validation_required"] is True
    assert f".mockup-validation/{feature_slug}/checklist.md" in payload["mockup_validation_missing"]


def test_penflow_contract_bootstrap_cli_accepts_source_penflow_dir(tmp_path: Path) -> None:
    source = tmp_path / "brainstorm-project" / "penflow"
    destination_project = tmp_path / "livespec-project"
    _write_json(source / "semantic-ui-tree.json", {"flows": [{"id": "onboarding"}], "screens": []})

    result = RUNNER.invoke(
        app,
        [
            "penflow-contract",
            "bootstrap",
            "--project",
            str(destination_project),
            "--source",
            str(source),
            "--json",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["copied"] is True
    assert payload["source"] == str(source)
    assert (destination_project / "penflow" / "semantic-ui-tree.json").exists()


def test_penflow_contract_status_cli_fails_raw_compare_fail(tmp_path: Path) -> None:
    (tmp_path / "penflow" / "flow-ui-contract").mkdir(parents=True)
    _write_json(
        tmp_path / "penflow" / "ui.pen",
        {"children": [{"type": "frame", "width": 1440, "height": 900}]},
    )
    _write_json(tmp_path / "penflow" / "semantic-ui-tree.json", {"flows": [], "screens": []})
    _write_json(tmp_path / "penflow" / "expected-ui-tree.json", {"screens": []})
    _write_json(tmp_path / "penflow" / "code-ir.json", {"flows": []})
    _write_json(tmp_path / "penflow" / "actual-ui-tree.json", {"screens": []})
    _write_json(
        tmp_path / "penflow" / "compare-report.json",
        {
            "status": "FAIL",
            "summary": {"errors": 0, "warnings": 245, "issues": 245},
            "issues": [{"code": "node.bbox.width", "severity": "warning"}],
        },
    )

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

    assert result.exit_code == 1, result.output
    payload = json.loads(result.output)
    assert payload["verdict"] == "FAIL"
    assert payload["runtime_comparison"] == "FAIL"
    assert payload["compare_status"] == "FAIL"
    assert payload["compare_issue_count"] == 1
