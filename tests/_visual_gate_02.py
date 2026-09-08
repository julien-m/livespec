"""Preserved test cases and fixtures for test_visual_gate.py."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests._visual_gate_01 import _write_spec
from validator.visual_gate import (
    _has_feature_scoped_penflow,
    _legacy_manifest_mockup_checks,
    _legacy_mockup_hash,
    _manifest_status_to_dict,
    _read_manifest_mapping,
    _read_spec_visual_marker,
    _resolve_legacy_mockup_path,
    _surfaces_yaml_mentions_feature,
    detect_visual_feature,
    promote_baseline,
)

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
