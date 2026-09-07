"""Preserved test cases and fixtures for test_visual_gate.py."""

from __future__ import annotations

import json
from pathlib import Path

from tests._visual_gate_01 import _png, _write_spec
from validator.penflow_contract import PenflowContractStatus, RuntimeComparisonState
from validator.visual_gate import (
    _aggregate_verdict,
    _alignment_dir_incomplete_reasons,
    _baseline_manifest_path,
    _resolve_manifest_source,
    _resolve_targets_for_check,
    _surfaces_yaml_mentions_feature,
    validate_gate,
)


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
