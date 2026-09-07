"""Preserved test cases and fixtures for test_visual_gate.py."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests._visual_gate_01 import _png, _write_spec
from validator.cli_exit_codes import (
    EXIT_OK,
    EXIT_VISUAL_GATE_BLOCKED,
    EXIT_VISUAL_GATE_FAIL,
)
from validator.visual_gate import (
    _detect_plain_copies,
    _read_alignment_manifest_sources,
    certify_visual_evidence,
    promote_baseline,
    validate_gate,
    verdict_to_exit_code,
)

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
