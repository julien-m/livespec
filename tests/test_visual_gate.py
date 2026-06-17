"""Unit tests for validator/visual_gate.py.

# @spec FR-100..103: Visual gate semantics — visual-gate-fix cycle
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from validator.cli_exit_codes import (
    EXIT_OK,
    EXIT_VISUAL_GATE_BLOCKED,
    EXIT_VISUAL_GATE_FAIL,
)
from validator.visual_gate import (
    VisualClassification,
    VisualFeatureSignals,
    apply_cleanup,
    detect_visual_feature,
    plan_cleanup,
    promote_baseline,
    render_text_report,
    validate_gate,
    verdict_to_exit_code,
    write_cleanup_report,
)


def _write_spec(project_root: Path, slug: str, *, marker: str | None) -> None:
    spec_dir = project_root / ".specs" / "features" / slug
    spec_dir.mkdir(parents=True, exist_ok=True)
    body = "# Spec\n\nbody\n"
    if marker is not None:
        body = f"---\n{marker}\n---\n\n" + body
    (spec_dir / "spec.md").write_text(body, encoding="utf-8")


def _png(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"png")


# ---------------------------------------------------------------------------
# Detection (P0-A)
# ---------------------------------------------------------------------------


def test_visual_classification_to_dict_includes_signals() -> None:
    signals = VisualFeatureSignals(
        s1_spec_marker=True,
        s1_spec_explicit_false=False,
        s2_feature_screens=True,
        s3_penflow_workspace=False,
        s4_flow_ui_contract=False,
        s5_feature_baselines=False,
        s6_surfaces_yaml=False,
    )
    payload = VisualClassification(
        classification="CONFLICT",
        signals=signals,
        conflict_reason="manual_review_required",
    ).to_dict()

    assert payload["classification"] == "CONFLICT"
    assert payload["signals"] == signals.to_dict()
    assert payload["conflict_reason"] == "manual_review_required"


def test_detect_visual_feature_returns_non_visual_when_marker_false(
    tmp_path: Path,
) -> None:
    slug = "001-no-ui"
    _write_spec(tmp_path, slug, marker="visual: false")
    classification = detect_visual_feature(project_root=tmp_path, feature_slug=slug)
    assert classification.classification == "NON_VISUAL"
    assert classification.signals.s1_spec_explicit_false is True


def test_detect_visual_feature_returns_visual_on_strong_signal_only(
    tmp_path: Path,
) -> None:
    slug = "002-screens-only"
    _write_spec(tmp_path, slug, marker=None)
    _png(tmp_path / ".specs/design/screens" / slug / "dashboard.png")
    classification = detect_visual_feature(project_root=tmp_path, feature_slug=slug)
    assert classification.classification == "VISUAL"
    assert classification.signals.strong_count >= 1


def test_detect_visual_feature_conflict_on_weak_signal_only(tmp_path: Path) -> None:
    slug = "003-weak-only"
    _write_spec(tmp_path, slug, marker=None)
    # Only s5 (baselines) -> weak signal
    _png(tmp_path / ".specs/features" / slug / "baselines" / "any.png")
    classification = detect_visual_feature(project_root=tmp_path, feature_slug=slug)
    assert classification.classification == "CONFLICT"
    assert classification.conflict_reason is not None
    assert "weak_signals_only" in classification.conflict_reason


def test_detect_visual_feature_conflict_when_spec_declares_but_no_artifacts(
    tmp_path: Path,
) -> None:
    slug = "004-declared-but-empty"
    _write_spec(tmp_path, slug, marker="visual: true")
    classification = detect_visual_feature(project_root=tmp_path, feature_slug=slug)
    assert classification.classification == "CONFLICT"
    assert classification.conflict_reason == "spec_declares_visual_but_no_artifacts"


def test_detect_visual_feature_returns_non_visual_without_spec_or_signals(
    tmp_path: Path,
) -> None:
    classification = detect_visual_feature(project_root=tmp_path, feature_slug="005-empty")

    assert classification.classification == "NON_VISUAL"
    assert classification.signals.strong_count == 0
    assert classification.signals.weak_count == 0


def test_detect_visual_feature_uses_feature_scoped_penflow_index(tmp_path: Path) -> None:
    slug = "006-penflow-index"
    _write_spec(tmp_path, slug, marker=None)
    penflow = tmp_path / "penflow"
    penflow.mkdir()
    (penflow / "index.yaml").write_text(f"features:\n  - {slug}\n", encoding="utf-8")

    classification = detect_visual_feature(project_root=tmp_path, feature_slug=slug)

    assert classification.classification == "VISUAL"
    assert classification.signals.s3_penflow_workspace is True


def test_detect_visual_feature_surfaces_yaml_is_weak_signal(tmp_path: Path) -> None:
    slug = "007-surfaces"
    _write_spec(tmp_path, slug, marker=None)
    (tmp_path / ".specs").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".specs" / "surfaces.yaml").write_text(
        f"surfaces:\n  - id: {slug}-dashboard\n    runner: playwright\n",
        encoding="utf-8",
    )

    classification = detect_visual_feature(project_root=tmp_path, feature_slug=slug)

    assert classification.classification == "CONFLICT"
    assert classification.signals.s6_surfaces_yaml is True
    assert "s6_surfaces_yaml" in str(classification.conflict_reason)


# ---------------------------------------------------------------------------
# Verdict aggregation
# ---------------------------------------------------------------------------


def test_validate_gate_passes_when_no_artifacts_required_and_no_conflicts(
    tmp_path: Path,
) -> None:
    slug = "010-pass"
    _write_spec(tmp_path, slug, marker="visual: false")
    report = validate_gate(
        project_root=tmp_path,
        feature_slug=slug,
        command="spec-check",
        target=None,
        strict_links=True,
    )
    assert report.verdict == "PASS"
    assert verdict_to_exit_code(report.verdict) == EXIT_OK


def test_validate_gate_blocked_on_classification_conflict(tmp_path: Path) -> None:
    slug = "011-blocked"
    _write_spec(tmp_path, slug, marker="visual: true")
    report = validate_gate(
        project_root=tmp_path,
        feature_slug=slug,
        command="spec-test",
        target="web",
        strict_links=True,
    )
    assert report.verdict == "BLOCKED"
    assert verdict_to_exit_code(report.verdict) == EXIT_VISUAL_GATE_BLOCKED
    assert report.conflict_reason == "spec_declares_visual_but_no_artifacts"


def test_validate_gate_fails_on_runtime_capture_misplaced_under_design_screens(
    tmp_path: Path,
) -> None:
    slug = "012-misplaced"
    _write_spec(tmp_path, slug, marker=None)
    payload = b"runtime-png"

    def _png_with(p: Path) -> None:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(payload)

    _png_with(tmp_path / ".specs/design/screens" / slug / "dash.png")
    _png_with(tmp_path / ".specs/design/baselines" / slug / "web" / "dash.png")
    report = validate_gate(
        project_root=tmp_path,
        feature_slug=slug,
        command="spec-check",
        target="web",
        strict_links=True,
    )
    assert report.verdict == "FAIL"
    assert verdict_to_exit_code(report.verdict) == EXIT_VISUAL_GATE_FAIL
    assert report.runtime_in_design_screens_violations


def test_validate_gate_fails_on_physical_copy_in_feature_baselines(tmp_path: Path) -> None:
    slug = "013-physical-copy"
    _write_spec(tmp_path, slug, marker=None)
    # Strong signal (screens) → VISUAL
    payload_design = b"design"

    def _make(p: Path, b: bytes) -> None:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b)

    _make(tmp_path / ".specs/design/screens" / slug / "dash.png", b"mockup")
    # Approved baseline registry must exist so the "missing_artifacts" path
    # does not pre-empt the link verdict.
    _make(tmp_path / ".specs/design/baselines" / slug / "web" / "dash.png", payload_design)
    # Feature-local PLAIN PNG (not symlink) → physical_copy_where_link_required
    _make(tmp_path / ".specs/features" / slug / "baselines" / "dash.png", payload_design)
    report = validate_gate(
        project_root=tmp_path,
        feature_slug=slug,
        command="spec-feature",
        target="web",
        strict_links=True,
    )
    assert report.verdict == "FAIL"
    assert any(v.kind == "physical_copy_where_link_required" for v in report.link_violations)


def test_render_text_report_includes_verdict_and_classification(tmp_path: Path) -> None:
    slug = "020-render"
    _write_spec(tmp_path, slug, marker="visual: false")
    report = validate_gate(
        project_root=tmp_path,
        feature_slug=slug,
        command="spec-check",
        target=None,
    )
    text = render_text_report(report)
    assert "Visual Gate Verdict: PASS" in text
    assert "classification=NON_VISUAL" in text


def test_render_text_report_includes_all_diagnostic_sections(tmp_path: Path) -> None:
    from validator.design_alignment.models import AlignmentResult
    from validator.penflow_contract import PenflowContractStatus
    from validator.registry_links import LinkViolation
    from validator.visual_gate import GateReport, VisualFeatureSignals

    report = GateReport(
        feature_slug="021-render-full",
        command="spec-check",
        target="web",
        classification="VISUAL",
        signals=VisualFeatureSignals(
            s1_spec_marker=True,
            s1_spec_explicit_false=False,
            s2_feature_screens=True,
            s3_penflow_workspace=True,
            s4_flow_ui_contract=True,
            s5_feature_baselines=False,
            s6_surfaces_yaml=False,
        ),
        verdict="BLOCKED",
        conflict_reason="manual-conflict",
        penflow=PenflowContractStatus(
            workspace=tmp_path / "penflow",
            state="ready",
            runtime_comparison="BLOCKED",
        ),
        alignment=[AlignmentResult(screen="dash", verdict="BLOCKED")],
        link_violations=[
            LinkViolation(
                kind="registry_path_missing",
                feature_slug="021-render-full",
                target="web",
                screen="dash",
                path=tmp_path / "missing.png",
                message="registry missing",
            )
        ],
        runtime_in_design_screens_violations=[tmp_path / ".specs/design/screens/dash.png"],
        visual_evidence={"verdict": "BLOCKED", "receipt_path": "receipt.json"},
        missing_artifacts=["missing-baseline"],
    )

    text = render_text_report(report)

    assert "conflict_reason: manual-conflict" in text
    assert "missing artifacts:" in text
    assert "link violations:" in text
    assert "runtime captures misplaced" in text
    assert "visual evidence:" in text
    assert "design-alignment screens:" in text
    assert "penflow: state=ready runtime_comparison=BLOCKED" in text


# ---------------------------------------------------------------------------
# Cleanup (P0-D)
# ---------------------------------------------------------------------------


def test_plan_cleanup_lists_misplaced_runtime_captures(tmp_path: Path) -> None:
    slug = "030-clean"
    payload = b"shared"
    src = tmp_path / ".specs/design/screens" / slug / "dash.png"
    base = tmp_path / ".specs/design/baselines" / slug / "web" / "dash.png"
    for p in (src, base):
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(payload)

    plan = plan_cleanup(
        project_root=tmp_path,
        feature_slug=slug,
        timestamp="20260523T000000Z",
    )
    assert plan.has_drift
    assert plan.actions[0].source == src
    assert plan.actions[0].kind == "archive"


def test_apply_cleanup_quarantines_files_and_is_idempotent(tmp_path: Path) -> None:
    slug = "031-apply"
    payload = b"shared"
    src = tmp_path / ".specs/design/screens" / slug / "dash.png"
    base = tmp_path / ".specs/design/baselines" / slug / "web" / "dash.png"
    for p in (src, base):
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(payload)

    plan = plan_cleanup(
        project_root=tmp_path,
        feature_slug=slug,
        timestamp="20260523T000001Z",
    )
    applied = apply_cleanup(plan)
    assert applied
    assert not src.exists()
    assert plan.quarantine_root and plan.quarantine_root.exists()

    # Second run: no drift, no actions.
    plan2 = plan_cleanup(
        project_root=tmp_path,
        feature_slug=slug,
        timestamp="20260523T000002Z",
    )
    assert not plan2.has_drift
    assert apply_cleanup(plan2) == []


def test_apply_cleanup_delete_mode_removes_misplaced_files(tmp_path: Path) -> None:
    slug = "031-delete"
    payload = b"shared"
    src = tmp_path / ".specs/design/screens" / slug / "dash.png"
    base = tmp_path / ".specs/design/baselines" / slug / "web" / "dash.png"
    for path in (src, base):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)

    plan = plan_cleanup(
        project_root=tmp_path,
        feature_slug=slug,
        timestamp="20260523T000003Z",
        mode="delete",
    )
    applied = apply_cleanup(plan)

    assert applied
    assert not src.exists()
    assert plan.quarantine_root is None


def test_write_cleanup_report_produces_json(tmp_path: Path) -> None:
    slug = "032-report"
    plan = plan_cleanup(project_root=tmp_path, feature_slug=slug, timestamp="20260523T000010Z")
    report_path = write_cleanup_report(
        project_root=tmp_path,
        plan=plan,
        applied=[],
        timestamp="20260523T000010Z",
    )
    assert report_path.exists()
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert payload["feature_slug"] == slug
    assert payload["has_drift"] is False


# ---------------------------------------------------------------------------
# Promote (P0-D follow-up)
# ---------------------------------------------------------------------------


def test_promote_baseline_creates_registry_copy_and_relative_symlink(
    tmp_path: Path,
) -> None:
    slug = "040-promote"
    run_capture = (
        tmp_path / ".specs/features" / slug / "run" / "20260523T000000Z" / "web" / "dash.png"
    )
    run_capture.parent.mkdir(parents=True, exist_ok=True)
    run_capture.write_bytes(b"runtime")

    registry, local = promote_baseline(
        project_root=tmp_path,
        feature_slug=slug,
        target="web",
        screen="dash",
        run_id="20260523T000000Z",
    )
    assert registry.exists()
    assert registry.read_bytes() == b"runtime"
    assert local is not None
    assert local.is_symlink()
    # Resolve goes back to the registry copy:
    assert local.resolve() == registry.resolve()


def test_promote_baseline_raises_for_missing_run_capture(tmp_path: Path) -> None:
    slug = "041-promote-missing"
    with pytest.raises(FileNotFoundError):
        promote_baseline(
            project_root=tmp_path,
            feature_slug=slug,
            target="web",
            screen="dash",
            run_id="20260523T000000Z",
        )


def test_promote_baseline_manifest_mode_persists_manifest_entry(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    slug = "042-promote-manifest"
    run_capture = (
        tmp_path / ".specs/features" / slug / "run" / "20260523T000000Z" / "web" / "dash.png"
    )
    run_capture.parent.mkdir(parents=True, exist_ok=True)
    run_capture.write_bytes(b"runtime")
    monkeypatch.setattr("validator.visual_gate.detect_link_capability", lambda _root: "manifest")

    registry, local = promote_baseline(
        project_root=tmp_path,
        feature_slug=slug,
        target="web",
        screen="dash",
        run_id="20260523T000000Z",
    )

    manifest = tmp_path / ".specs/features" / slug / "baselines" / "manifest.json"
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    assert registry.exists()
    assert local is None
    assert payload["entries"][0]["screen"] == "dash"
    assert payload["entries"][0]["registry_path"].endswith("dash.png")
