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
from validator.penflow_contract import PenflowContractStatus, RuntimeComparisonState
from validator.visual_gate import (
    GateReport,
    VisualClassification,
    VisualFeatureSignals,
    _aggregate_verdict,
    _alignment_dir_incomplete_reasons,
    _baseline_manifest_path,
    _detect_plain_copies,
    _has_feature_scoped_penflow,
    _legacy_manifest_mockup_checks,
    _legacy_mockup_hash,
    _manifest_status_to_dict,
    _read_alignment_manifest_sources,
    _read_manifest_mapping,
    _read_spec_visual_marker,
    _resolve_legacy_mockup_path,
    _resolve_manifest_source,
    _resolve_targets_for_check,
    _surfaces_yaml_mentions_feature,
    apply_cleanup,
    certify_visual_evidence,
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
    from validator.visual_gate import VisualFeatureSignals

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


# ---------------------------------------------------------------------------
# Coverage: malformed manifests and legacy checks
# ---------------------------------------------------------------------------


def test_legacy_manifest_non_list_screens_returns_empty(tmp_path: Path) -> None:
    slug = "100-manifest"
    feat = tmp_path / ".specs/features" / slug
    feat.mkdir(parents=True)
    (feat / "baselines" / "baseline.manifest.yml").parent.mkdir(parents=True)
    (feat / "baselines" / "baseline.manifest.yml").write_text(
        'screens: "not a list"\n', encoding="utf-8"
    )
    missing, violations = _legacy_manifest_mockup_checks(
        manifest_path=feat / "baselines" / "baseline.manifest.yml",
        project_root=tmp_path,
        feature_slug=slug,
    )
    assert missing == []
    assert violations == []


def test_legacy_manifest_non_mapping_entry_skipped(tmp_path: Path) -> None:
    slug = "101-manifest"
    feat = tmp_path / ".specs/features" / slug
    feat.mkdir(parents=True)
    (feat / "baselines" / "baseline.manifest.yml").parent.mkdir(parents=True)
    (feat / "baselines" / "baseline.manifest.yml").write_text(
        "screens:\n  - 42\n  - true\n", encoding="utf-8"
    )
    missing, violations = _legacy_manifest_mockup_checks(
        manifest_path=feat / "baselines" / "baseline.manifest.yml",
        project_root=tmp_path,
        feature_slug=slug,
    )
    assert missing == []
    assert violations == []


def test_legacy_manifest_empty_screen_skipped(tmp_path: Path) -> None:
    slug = "102-manifest"
    feat = tmp_path / ".specs/features" / slug
    feat.mkdir(parents=True)
    (feat / "baselines" / "baseline.manifest.yml").parent.mkdir(parents=True)
    (feat / "baselines" / "baseline.manifest.yml").write_text(
        'screens:\n  - screen: ""\n  - screen: "  "\n', encoding="utf-8"
    )
    missing, violations = _legacy_manifest_mockup_checks(
        manifest_path=feat / "baselines" / "baseline.manifest.yml",
        project_root=tmp_path,
        feature_slug=slug,
    )
    assert missing == []
    assert violations == []


def test_legacy_manifest_mockup_path_escape_detected(tmp_path: Path) -> None:
    slug = "103-escape"
    feat = tmp_path / ".specs/features" / slug
    feat.mkdir(parents=True)
    screens_dir = tmp_path / ".specs/design/screens" / slug
    screens_dir.mkdir(parents=True)
    (screens_dir / "dash.png").write_bytes(b"png")
    manifest = feat / "baselines" / "baseline.manifest.yml"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        'screens:\n  - screen: dash\n    mockup_path: "../../etc/passwd"\n',
        encoding="utf-8",
    )
    _missing, violations = _legacy_manifest_mockup_checks(
        manifest_path=manifest,
        project_root=tmp_path,
        feature_slug=slug,
    )
    assert any(v.kind == "manifest_unreadable" for v in violations)


def test_legacy_manifest_mockup_version_non_string(tmp_path: Path) -> None:
    slug = "104-version"
    feat = tmp_path / ".specs/features" / slug
    screens_dir = tmp_path / ".specs/design/screens" / slug
    screens_dir.mkdir(parents=True)
    (screens_dir / "dash.png").write_bytes(b"png")
    manifest = feat / "baselines" / "baseline.manifest.yml"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        "screens:\n  - screen: dash\n    mockup_version: 42\n",
        encoding="utf-8",
    )
    missing, _violations = _legacy_manifest_mockup_checks(
        manifest_path=manifest,
        project_root=tmp_path,
        feature_slug=slug,
    )
    assert any("mockup_version" in m for m in missing)


def test_legacy_manifest_mockup_version_no_sha256_prefix(tmp_path: Path) -> None:
    slug = "105-prefix"
    feat = tmp_path / ".specs/features" / slug
    screens_dir = tmp_path / ".specs/design/screens" / slug
    screens_dir.mkdir(parents=True)
    (screens_dir / "dash.png").write_bytes(b"png")
    manifest = feat / "baselines" / "baseline.manifest.yml"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        'screens:\n  - screen: dash\n    mockup_version: "abc123"\n',
        encoding="utf-8",
    )
    missing, _violations = _legacy_manifest_mockup_checks(
        manifest_path=manifest,
        project_root=tmp_path,
        feature_slug=slug,
    )
    assert any("mockup_version" in m for m in missing)


def test_legacy_manifest_mockup_version_short_digest(tmp_path: Path) -> None:
    slug = "106-digest"
    feat = tmp_path / ".specs/features" / slug
    screens_dir = tmp_path / ".specs/design/screens" / slug
    screens_dir.mkdir(parents=True)
    (screens_dir / "dash.png").write_bytes(b"png")
    manifest = feat / "baselines" / "baseline.manifest.yml"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        'screens:\n  - screen: dash\n    mockup_version: "sha256:abc"\n',
        encoding="utf-8",
    )
    missing, _violations = _legacy_manifest_mockup_checks(
        manifest_path=manifest,
        project_root=tmp_path,
        feature_slug=slug,
    )
    assert any("mockup_version" in m for m in missing)


def test_legacy_manifest_mockup_hash_helpers() -> None:
    assert _legacy_mockup_hash({}) is None
    assert _legacy_mockup_hash({"mockup_version": 42}) is None
    assert _legacy_mockup_hash({"mockup_version": "nope"}) is None
    assert _legacy_mockup_hash({"mockup_version": "sha256:abc"}) is None
    good = "sha256:" + "a" * 64
    assert _legacy_mockup_hash({"mockup_version": good}) == "a" * 64


def test_read_manifest_mapping_returns_none_for_unreadable(tmp_path: Path) -> None:
    p = tmp_path / "missing.json"
    assert _read_manifest_mapping(p) is None


def test_read_manifest_mapping_returns_none_for_malformed_json(tmp_path: Path) -> None:
    p = tmp_path / "bad.json"
    p.write_text("not json{{{", encoding="utf-8")
    assert _read_manifest_mapping(p) is None


def test_read_manifest_mapping_returns_none_for_malformed_yaml(tmp_path: Path) -> None:
    p = tmp_path / "bad.yml"
    p.write_text(":\n  :\n    - ][", encoding="utf-8")
    result = _read_manifest_mapping(p)
    assert result is None or isinstance(result, dict)


def test_read_manifest_mapping_returns_none_for_non_mapping(tmp_path: Path) -> None:
    p = tmp_path / "list.json"
    p.write_text("[1, 2, 3]", encoding="utf-8")
    assert _read_manifest_mapping(p) is None


def test_resolve_legacy_mockup_path_absolute_escape(tmp_path: Path) -> None:
    slug = "107-abs"
    screens_dir = tmp_path / ".specs/design/screens" / slug
    screens_dir.mkdir(parents=True)
    raw: dict[str, object] = {"mockup_path": "/etc/passwd"}
    _path, err = _resolve_legacy_mockup_path(
        raw, project_root=tmp_path, feature_slug=slug, screen="dash"
    )
    assert err is not None
    assert "escapes" in err


def test_resolve_legacy_mockup_path_relative_escape(tmp_path: Path) -> None:
    slug = "108-rel"
    screens_dir = tmp_path / ".specs/design/screens" / slug
    screens_dir.mkdir(parents=True)
    raw: dict[str, object] = {"mockup_path": "../../other/file.png"}
    _path, err = _resolve_legacy_mockup_path(
        raw, project_root=tmp_path, feature_slug=slug, screen="dash"
    )
    assert err is not None
    assert "escapes" in err


# ---------------------------------------------------------------------------
# Coverage: manifest status dict
# ---------------------------------------------------------------------------


def test_manifest_status_to_dict_none() -> None:
    assert _manifest_status_to_dict(None) is None


# ---------------------------------------------------------------------------
# Coverage: spec read errors and detection branches
# ---------------------------------------------------------------------------


def test_read_spec_marker_unreadable_file(tmp_path: Path) -> None:
    spec = tmp_path / "spec.md"
    spec.write_text("content", encoding="utf-8")
    spec.chmod(0o000)
    try:
        has, false = _read_spec_visual_marker(spec)
        assert has is False
        assert false is False
    finally:
        spec.chmod(0o644)


def test_read_spec_marker_no_closing_delimiter(tmp_path: Path) -> None:
    spec = tmp_path / "spec.md"
    spec.write_text("---\nvisual: true\n# no closing delimiter", encoding="utf-8")
    has, _false = _read_spec_visual_marker(spec)
    assert has is True


def test_detect_visual_conflict_weak_only_surfaces(tmp_path: Path) -> None:
    slug = "109-surfaces"
    _write_spec(tmp_path, slug, marker=None)
    (tmp_path / ".specs").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".specs" / "surfaces.yaml").write_text(
        f"surfaces:\n  - id: {slug}-ui\n    runner: playwright\n",
        encoding="utf-8",
    )
    classification = detect_visual_feature(project_root=tmp_path, feature_slug=slug)
    assert classification.classification == "CONFLICT"
    assert classification.signals.s6_surfaces_yaml is True


# ---------------------------------------------------------------------------
# Coverage: penflow index read failure
# ---------------------------------------------------------------------------


def test_penflow_index_read_oserror_skipped(tmp_path: Path) -> None:
    penflow = tmp_path / "penflow"
    penflow.mkdir()
    idx = penflow / "index.yaml"
    idx.write_text("features:\n  - test\n", encoding="utf-8")
    idx.chmod(0o000)
    try:
        result = _has_feature_scoped_penflow(tmp_path, "test")
        assert result is False
    finally:
        idx.chmod(0o644)


def test_penflow_index_yml_detected(tmp_path: Path) -> None:
    penflow = tmp_path / "penflow"
    penflow.mkdir()
    (penflow / "index.yml").write_text("features:\n  - my-feature\n", encoding="utf-8")
    assert _has_feature_scoped_penflow(tmp_path, "my-feature") is True


# ---------------------------------------------------------------------------
# Coverage: surfaces.yaml parsing edge cases
# ---------------------------------------------------------------------------


def test_surfaces_yaml_oserror_returns_false(tmp_path: Path) -> None:
    (tmp_path / ".specs").mkdir(parents=True)
    s = tmp_path / ".specs" / "surfaces.yaml"
    s.write_text("surfaces:\n  - id: test\n", encoding="utf-8")
    s.chmod(0o000)
    try:
        assert _surfaces_yaml_mentions_feature(tmp_path, "test") is False
    finally:
        s.chmod(0o644)


def test_surfaces_yaml_non_mapping_root_returns_false(tmp_path: Path) -> None:
    (tmp_path / ".specs").mkdir(parents=True)
    (tmp_path / ".specs" / "surfaces.yaml").write_text('"just a string"', encoding="utf-8")
    assert _surfaces_yaml_mentions_feature(tmp_path, "test") is False


def test_surfaces_yaml_non_mapping_entry_skipped(tmp_path: Path) -> None:
    (tmp_path / ".specs").mkdir(parents=True)
    (tmp_path / ".specs" / "surfaces.yaml").write_text(
        "surfaces:\n  - 42\n  - true\n", encoding="utf-8"
    )
    assert _surfaces_yaml_mentions_feature(tmp_path, "test") is False


def test_surfaces_yaml_features_list_top_level(tmp_path: Path) -> None:
    (tmp_path / ".specs").mkdir(parents=True)
    (tmp_path / ".specs" / "surfaces.yaml").write_text("features:\n  - my-slug\n", encoding="utf-8")
    assert _surfaces_yaml_mentions_feature(tmp_path, "my-slug") is True


def test_surfaces_yaml_features_map_top_level(tmp_path: Path) -> None:
    (tmp_path / ".specs").mkdir(parents=True)
    (tmp_path / ".specs" / "surfaces.yaml").write_text(
        "features:\n  my-slug:\n    runner: playwright\n", encoding="utf-8"
    )
    assert _surfaces_yaml_mentions_feature(tmp_path, "my-slug") is True


def test_surfaces_yaml_entry_features_list(tmp_path: Path) -> None:
    (tmp_path / ".specs").mkdir(parents=True)
    (tmp_path / ".specs" / "surfaces.yaml").write_text(
        "surfaces:\n  - id: dashboard\n    features:\n      - my-slug\n",
        encoding="utf-8",
    )
    assert _surfaces_yaml_mentions_feature(tmp_path, "my-slug") is True


# ---------------------------------------------------------------------------
# Coverage: manifest source resolution
# ---------------------------------------------------------------------------


def test_resolve_manifest_source_empty_returns_none() -> None:
    assert _resolve_manifest_source("", screen_dir=Path("/tmp"), project_root=Path("/tmp")) is None


def test_resolve_manifest_source_absolute_path(tmp_path: Path) -> None:
    target = tmp_path / "abs.png"
    target.write_bytes(b"png")
    result = _resolve_manifest_source(str(target), screen_dir=tmp_path, project_root=tmp_path)
    assert result == target


def test_resolve_manifest_source_absolute_missing(tmp_path: Path) -> None:
    result = _resolve_manifest_source(
        "/nonexistent/file.png", screen_dir=tmp_path, project_root=tmp_path
    )
    assert result is None


def test_resolve_manifest_source_specs_relative(tmp_path: Path) -> None:
    target = tmp_path / ".specs" / "design" / "file.png"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"png")
    result = _resolve_manifest_source(
        ".specs/design/file.png", screen_dir=tmp_path, project_root=tmp_path
    )
    assert result == target


def test_resolve_manifest_source_local_relative(tmp_path: Path) -> None:
    screen_dir = tmp_path / "screen"
    screen_dir.mkdir()
    target = screen_dir / "local.png"
    target.write_bytes(b"png")
    result = _resolve_manifest_source("local.png", screen_dir=screen_dir, project_root=tmp_path)
    assert result == target.resolve()


def test_resolve_manifest_source_rooted_relative(tmp_path: Path) -> None:
    target = tmp_path / "rooted.png"
    target.write_bytes(b"png")
    result = _resolve_manifest_source(
        "rooted.png", screen_dir=tmp_path / "nonexistent", project_root=tmp_path
    )
    assert result == target.resolve()


# ---------------------------------------------------------------------------
# Coverage: alignment dir incomplete reasons
# ---------------------------------------------------------------------------


def test_alignment_dir_incomplete_no_manifest_no_files(tmp_path: Path) -> None:
    screen_dir = tmp_path / "screen"
    screen_dir.mkdir()
    reasons = _alignment_dir_incomplete_reasons(screen_dir, project_root=tmp_path)
    assert len(reasons) == 2


def test_alignment_dir_incomplete_manifest_with_error(tmp_path: Path) -> None:
    screen_dir = tmp_path / "screen"
    screen_dir.mkdir()
    (screen_dir / "design-alignment.manifest.json").write_text(
        '{"design_source": "missing.png"}', encoding="utf-8"
    )
    reasons = _alignment_dir_incomplete_reasons(screen_dir, project_root=tmp_path)
    assert len(reasons) == 1
    assert "missing" in reasons[0].lower() or "runtime_source" in reasons[0]


def test_alignment_dir_incomplete_manifest_ok(tmp_path: Path) -> None:
    screen_dir = tmp_path / "screen"
    screen_dir.mkdir()
    d = screen_dir / "d.json"
    r = screen_dir / "r.json"
    d.write_text("{}", encoding="utf-8")
    r.write_text("{}", encoding="utf-8")
    (screen_dir / "design-alignment.manifest.json").write_text(
        json.dumps({"design_source": "d.json", "runtime_source": "r.json"}),
        encoding="utf-8",
    )
    reasons = _alignment_dir_incomplete_reasons(screen_dir, project_root=tmp_path)
    assert reasons == []


# ---------------------------------------------------------------------------
# Coverage: baseline manifest path JSON fallback
# ---------------------------------------------------------------------------


def test_baseline_manifest_path_json_fallback(tmp_path: Path) -> None:
    slug = "110-json"
    base = tmp_path / ".specs/features" / slug / "baselines"
    base.mkdir(parents=True)
    (base / "manifest.json").write_text("{}", encoding="utf-8")
    result = _baseline_manifest_path(tmp_path, slug)
    assert result == base / "manifest.json"


# ---------------------------------------------------------------------------
# Coverage: strict_links=False path
# ---------------------------------------------------------------------------


def test_validate_gate_strict_links_disabled(tmp_path: Path) -> None:
    slug = "111-strict"
    _write_spec(tmp_path, slug, marker="visual: true")
    screens_dir = tmp_path / ".specs/design/screens" / slug
    _png(screens_dir / "dash.png")
    report = validate_gate(
        project_root=tmp_path,
        feature_slug=slug,
        command="spec-check",
        target="web",
        strict_links=False,
    )
    assert report.classification == "VISUAL"


# ---------------------------------------------------------------------------
# Coverage: target resolution
# ---------------------------------------------------------------------------


def test_resolve_targets_explicit_target() -> None:
    result = _resolve_targets_for_check(project_root=Path("/tmp"), feature_slug="x", target="ios")
    assert result == ["ios"]


def test_resolve_targets_from_baselines_registry(tmp_path: Path) -> None:
    slug = "112-targets"
    base = tmp_path / ".specs/design/baselines" / slug / "web"
    base.mkdir(parents=True)
    (base / "dash.png").write_bytes(b"png")
    result = _resolve_targets_for_check(project_root=tmp_path, feature_slug=slug, target=None)
    assert result == ["web"]


def test_resolve_targets_from_surfaces_yaml(tmp_path: Path) -> None:
    slug = "113-surfaces"
    (tmp_path / ".specs").mkdir(parents=True)
    (tmp_path / ".specs" / "surfaces.yaml").write_text(
        "surfaces:\n  - id: ui\n    runner: maestro\n", encoding="utf-8"
    )
    result = _resolve_targets_for_check(project_root=tmp_path, feature_slug=slug, target=None)
    assert "android" in result


def test_resolve_targets_empty_when_nothing(tmp_path: Path) -> None:
    result = _resolve_targets_for_check(project_root=tmp_path, feature_slug="nope", target=None)
    assert result == []


def test_resolve_targets_surfaces_non_mapping_root(tmp_path: Path) -> None:
    (tmp_path / ".specs").mkdir(parents=True)
    (tmp_path / ".specs" / "surfaces.yaml").write_text('"string"', encoding="utf-8")
    result = _resolve_targets_for_check(project_root=tmp_path, feature_slug="x", target=None)
    assert result == []


def test_resolve_targets_surfaces_non_mapping_entry(tmp_path: Path) -> None:
    (tmp_path / ".specs").mkdir(parents=True)
    (tmp_path / ".specs" / "surfaces.yaml").write_text("surfaces:\n  - 42\n", encoding="utf-8")
    result = _resolve_targets_for_check(project_root=tmp_path, feature_slug="x", target=None)
    assert result == []


def test_resolve_targets_surfaces_unknown_runner(tmp_path: Path) -> None:
    (tmp_path / ".specs").mkdir(parents=True)
    (tmp_path / ".specs" / "surfaces.yaml").write_text(
        "surfaces:\n  - id: x\n    runner: unknown\n", encoding="utf-8"
    )
    result = _resolve_targets_for_check(project_root=tmp_path, feature_slug="x", target=None)
    assert result == []


# ---------------------------------------------------------------------------
# Coverage: aggregate verdict branches
# ---------------------------------------------------------------------------


def _make_penflow(runtime_comparison: RuntimeComparisonState) -> PenflowContractStatus:
    return PenflowContractStatus(
        workspace=Path("/tmp"), state="ready", runtime_comparison=runtime_comparison
    )


def test_aggregate_verdict_visual_evidence_fail() -> None:
    verdict = _aggregate_verdict(
        penflow=_make_penflow("READY"),
        alignment=[],
        link_violations=[],
        runtime_misplaced=[],
        missing_artifacts=[],
        visual_evidence_verdict="FAIL",
    )
    assert verdict == "FAIL"


def test_aggregate_verdict_penflow_fail() -> None:
    verdict = _aggregate_verdict(
        penflow=_make_penflow("FAIL"),
        alignment=[],
        link_violations=[],
        runtime_misplaced=[],
        missing_artifacts=[],
        visual_evidence_verdict=None,
    )
    assert verdict == "FAIL"


def test_aggregate_verdict_visual_evidence_blocked() -> None:
    verdict = _aggregate_verdict(
        penflow=_make_penflow("READY"),
        alignment=[],
        link_violations=[],
        runtime_misplaced=[],
        missing_artifacts=[],
        visual_evidence_verdict="BLOCKED",
    )
    assert verdict == "BLOCKED"


def test_aggregate_verdict_alignment_blocked() -> None:
    from validator.design_alignment.models import AlignmentResult

    verdict = _aggregate_verdict(
        penflow=_make_penflow("READY"),
        alignment=[AlignmentResult(screen="dash", verdict="BLOCKED")],
        link_violations=[],
        runtime_misplaced=[],
        missing_artifacts=[],
        visual_evidence_verdict=None,
    )
    assert verdict == "BLOCKED"


def test_aggregate_verdict_penflow_blocked() -> None:
    verdict = _aggregate_verdict(
        penflow=_make_penflow("BLOCKED"),
        alignment=[],
        link_violations=[],
        runtime_misplaced=[],
        missing_artifacts=[],
        visual_evidence_verdict=None,
    )
    assert verdict == "BLOCKED"


def test_aggregate_verdict_missing_artifacts_blocked() -> None:
    verdict = _aggregate_verdict(
        penflow=_make_penflow("READY"),
        alignment=[],
        link_violations=[],
        runtime_misplaced=[],
        missing_artifacts=["something"],
        visual_evidence_verdict=None,
    )
    assert verdict == "BLOCKED"


def test_aggregate_verdict_pass() -> None:
    verdict = _aggregate_verdict(
        penflow=_make_penflow("READY"),
        alignment=[],
        link_violations=[],
        runtime_misplaced=[],
        missing_artifacts=[],
        visual_evidence_verdict=None,
    )
    assert verdict == "PASS"


def test_aggregate_verdict_alignment_fail() -> None:
    from validator.design_alignment.models import AlignmentResult

    verdict = _aggregate_verdict(
        penflow=_make_penflow("READY"),
        alignment=[AlignmentResult(screen="dash", verdict="FAIL")],
        link_violations=[],
        runtime_misplaced=[],
        missing_artifacts=[],
        visual_evidence_verdict=None,
    )
    assert verdict == "FAIL"


def test_aggregate_verdict_link_violation_fail(tmp_path: Path) -> None:
    from validator.registry_links import LinkViolation

    verdict = _aggregate_verdict(
        penflow=_make_penflow("READY"),
        alignment=[],
        link_violations=[
            LinkViolation(
                kind="physical_copy_where_link_required",
                feature_slug="x",
                target="web",
                screen="dash",
                path=tmp_path / "file.png",
                message="copy",
            )
        ],
        runtime_misplaced=[],
        missing_artifacts=[],
        visual_evidence_verdict=None,
    )
    assert verdict == "FAIL"


def test_aggregate_verdict_link_violation_blocked(tmp_path: Path) -> None:
    from validator.registry_links import LinkViolation

    verdict = _aggregate_verdict(
        penflow=_make_penflow("READY"),
        alignment=[],
        link_violations=[
            LinkViolation(
                kind="manifest_missing_registry_path",
                feature_slug="x",
                target="web",
                screen="dash",
                path=tmp_path / "manifest.yml",
                message="missing",
            )
        ],
        runtime_misplaced=[],
        missing_artifacts=[],
        visual_evidence_verdict=None,
    )
    assert verdict == "BLOCKED"


# ---------------------------------------------------------------------------
# Coverage: manifest-mode promotion with existing manifest
# ---------------------------------------------------------------------------


def test_promote_baseline_manifest_mode_updates_existing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    slug = "114-update"
    run_capture = (
        tmp_path / ".specs/features" / slug / "run" / "20260523T000000Z" / "web" / "dash.png"
    )
    run_capture.parent.mkdir(parents=True)
    run_capture.write_bytes(b"runtime")
    manifest_dir = tmp_path / ".specs/features" / slug / "baselines"
    manifest_dir.mkdir(parents=True)
    existing = {
        "feature_slug": slug,
        "target": "web",
        "entries": [{"screen": "other", "kind": "ref", "registry_path": "x"}],
    }
    (manifest_dir / "manifest.json").write_text(json.dumps(existing), encoding="utf-8")
    monkeypatch.setattr("validator.visual_gate.detect_link_capability", lambda _root: "manifest")

    _registry, _local = promote_baseline(
        project_root=tmp_path,
        feature_slug=slug,
        target="web",
        screen="dash",
        run_id="20260523T000000Z",
    )

    payload = json.loads((manifest_dir / "manifest.json").read_text(encoding="utf-8"))
    screens = [e["screen"] for e in payload["entries"]]
    assert "dash" in screens
    assert "other" in screens


def test_promote_baseline_manifest_mode_replaces_same_screen(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    slug = "115-replace"
    run_capture = (
        tmp_path / ".specs/features" / slug / "run" / "20260523T000001Z" / "web" / "dash.png"
    )
    run_capture.parent.mkdir(parents=True)
    run_capture.write_bytes(b"runtime")
    manifest_dir = tmp_path / ".specs/features" / slug / "baselines"
    manifest_dir.mkdir(parents=True)
    existing = {
        "feature_slug": slug,
        "target": "web",
        "entries": [{"screen": "dash", "kind": "ref", "registry_path": "old/path"}],
    }
    (manifest_dir / "manifest.json").write_text(json.dumps(existing), encoding="utf-8")
    monkeypatch.setattr("validator.visual_gate.detect_link_capability", lambda _root: "manifest")

    promote_baseline(
        project_root=tmp_path,
        feature_slug=slug,
        target="web",
        screen="dash",
        run_id="20260523T000001Z",
    )

    payload = json.loads((manifest_dir / "manifest.json").read_text(encoding="utf-8"))
    dash_entries = [e for e in payload["entries"] if e["screen"] == "dash"]
    assert len(dash_entries) == 1
    assert "dash.png" in dash_entries[0]["registry_path"]


def test_promote_baseline_manifest_mode_corrupted_json(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    slug = "116-corrupt"
    run_capture = (
        tmp_path / ".specs/features" / slug / "run" / "20260523T000000Z" / "web" / "dash.png"
    )
    run_capture.parent.mkdir(parents=True)
    run_capture.write_bytes(b"runtime")
    manifest_dir = tmp_path / ".specs/features" / slug / "baselines"
    manifest_dir.mkdir(parents=True)
    (manifest_dir / "manifest.json").write_text("not json{{{", encoding="utf-8")
    monkeypatch.setattr("validator.visual_gate.detect_link_capability", lambda _root: "manifest")

    _registry, _local = promote_baseline(
        project_root=tmp_path,
        feature_slug=slug,
        target="web",
        screen="dash",
        run_id="20260523T000000Z",
    )

    payload = json.loads((manifest_dir / "manifest.json").read_text(encoding="utf-8"))
    assert payload["entries"][0]["screen"] == "dash"


# ---------------------------------------------------------------------------
# Coverage: read_alignment_manifest_sources edge cases
# ---------------------------------------------------------------------------


def test_read_alignment_manifest_sources_unreadable(tmp_path: Path) -> None:
    screen_dir = tmp_path / "screen"
    screen_dir.mkdir()
    manifest = screen_dir / "design-alignment.manifest.json"
    manifest.write_text("{}", encoding="utf-8")
    manifest.chmod(0o000)
    try:
        d, _r, err, _raw = _read_alignment_manifest_sources(screen_dir, project_root=tmp_path)
        assert d is None
        assert err is not None
        assert "unreadable" in err
    finally:
        manifest.chmod(0o644)


def test_read_alignment_manifest_sources_malformed_json(tmp_path: Path) -> None:
    screen_dir = tmp_path / "screen"
    screen_dir.mkdir()
    (screen_dir / "design-alignment.manifest.json").write_text("not json", encoding="utf-8")
    d, _r, err, _raw = _read_alignment_manifest_sources(screen_dir, project_root=tmp_path)
    assert d is None
    assert err is not None
    assert "malformed" in err


def test_read_alignment_manifest_sources_non_object(tmp_path: Path) -> None:
    screen_dir = tmp_path / "screen"
    screen_dir.mkdir()
    (screen_dir / "design-alignment.manifest.json").write_text("[1, 2]", encoding="utf-8")
    d, _r, err, _raw = _read_alignment_manifest_sources(screen_dir, project_root=tmp_path)
    assert d is None
    assert err is not None
    assert "object" in err


def test_read_alignment_manifest_sources_missing_fields(tmp_path: Path) -> None:
    screen_dir = tmp_path / "screen"
    screen_dir.mkdir()
    (screen_dir / "design-alignment.manifest.json").write_text('{"other": true}', encoding="utf-8")
    d, _r, err, _raw = _read_alignment_manifest_sources(screen_dir, project_root=tmp_path)
    assert d is None
    assert err is not None
    assert "missing" in err.lower() or "design_source" in err


def test_read_alignment_manifest_sources_unresolved(tmp_path: Path) -> None:
    screen_dir = tmp_path / "screen"
    screen_dir.mkdir()
    (screen_dir / "design-alignment.manifest.json").write_text(
        json.dumps({"design_source": "missing.png", "runtime_source": "also_missing.png"}),
        encoding="utf-8",
    )
    d, _r, err, _raw = _read_alignment_manifest_sources(screen_dir, project_root=tmp_path)
    assert d is None
    assert err is not None
    assert "unresolved" in err


# ---------------------------------------------------------------------------
# Coverage: receipt validation edge cases
# ---------------------------------------------------------------------------


def test_certify_blocked_when_threshold_out_of_range(tmp_path: Path) -> None:
    result = certify_visual_evidence(
        project_root=tmp_path,
        feature_slug="x",
        command="spec-check",
        target="web",
        run_id="manual",
        threshold_percent=-1,
    )
    assert result["verdict"] == "BLOCKED"


def test_certify_blocked_when_no_mockups(tmp_path: Path) -> None:
    result = certify_visual_evidence(
        project_root=tmp_path,
        feature_slug="x",
        command="spec-check",
        target="web",
        run_id="manual",
    )
    assert result["verdict"] == "BLOCKED"


# ---------------------------------------------------------------------------
# Coverage: validate_gate VISUAL path with missing targets
# ---------------------------------------------------------------------------


def test_validate_gate_visual_no_target_no_baselines_no_surfaces(tmp_path: Path) -> None:
    slug = "117-notarget"
    _write_spec(tmp_path, slug, marker="visual: true")
    report = validate_gate(
        project_root=tmp_path,
        feature_slug=slug,
        command="spec-check",
        target=None,
    )
    assert report.verdict == "BLOCKED"
    assert any("no target" in m.lower() or "target" in m.lower() for m in report.missing_artifacts)


# ---------------------------------------------------------------------------
# Coverage: _detect_plain_copies with broken symlinks
# ---------------------------------------------------------------------------


def test_detect_plain_copies_broken_symlink(tmp_path: Path) -> None:
    slug = "118-broken"
    base = tmp_path / ".specs/features" / slug / "baselines"
    base.mkdir(parents=True)
    link = base / "dash.png"
    link.symlink_to("/nonexistent/registry/file.png")
    violations = _detect_plain_copies(tmp_path, slug, "web")
    assert any(v.kind == "broken_symlink" for v in violations)


# ---------------------------------------------------------------------------
# Coverage: validate_gate VISUAL path with missing registry baselines
# ---------------------------------------------------------------------------


def test_validate_gate_visual_missing_registry_baselines(tmp_path: Path) -> None:
    slug = "119-missing-reg"
    _write_spec(tmp_path, slug, marker="visual: true")
    screens_dir = tmp_path / ".specs/design/screens" / slug
    _png(screens_dir / "dash.png")
    report = validate_gate(
        project_root=tmp_path,
        feature_slug=slug,
        command="spec-check",
        target="web",
    )
    assert report.verdict in ("BLOCKED", "FAIL")


# ---------------------------------------------------------------------------
# Coverage: verdict_to_exit_code branches
# ---------------------------------------------------------------------------


def test_verdict_to_exit_code_all() -> None:
    assert verdict_to_exit_code("PASS") == EXIT_OK
    assert verdict_to_exit_code("FAIL") == EXIT_VISUAL_GATE_FAIL
    assert verdict_to_exit_code("BLOCKED") == EXIT_VISUAL_GATE_BLOCKED


# ---------------------------------------------------------------------------
# Coverage: _as_mapping and _as_list
# ---------------------------------------------------------------------------


def test_as_mapping_returns_none_for_non_dict() -> None:
    from validator.visual_gate import _as_mapping

    assert _as_mapping("string") is None
    assert _as_mapping(42) is None
    assert _as_mapping([1, 2]) is None
    assert _as_mapping({"key": "value"}) == {"key": "value"}


def test_as_list_returns_none_for_non_list() -> None:
    from validator.visual_gate import _as_list

    assert _as_list("string") is None
    assert _as_list(42) is None
    assert _as_list({"key": "value"}) is None
    assert _as_list([1, 2]) == [1, 2]
