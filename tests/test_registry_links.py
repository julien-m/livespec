"""Unit tests for validator/registry_links.py.

# @spec FR-001..003: Registry-link contract — visual-gate-fix cycle
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from validator.registry_links import (
    LinkViolation,
    check_link,
    detect_link_capability,
    expected_feature_local_path,
    expected_registry_baseline_path,
    expected_registry_mockup_path,
    find_runtime_misplaced_under_design_screens,
    is_runtime_capture_misplaced,
    read_link_mode,
    sha256_of,
    validate_manifest,
    write_link_mode,
)


def _make_png(path: Path, payload: bytes = b"png-bytes") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def test_expected_registry_paths_match_canonical_layout() -> None:
    baseline = expected_registry_baseline_path(
        feature_slug="001-foo", target="web", screen="dashboard"
    )
    assert baseline == Path(".specs/design/baselines/001-foo/web/dashboard.png")

    mockup = expected_registry_mockup_path(
        feature_slug="001-foo", screen="dashboard.png"
    )
    assert mockup == Path(".specs/design/screens/001-foo/dashboard.png")

    local = expected_feature_local_path(
        feature_slug="001-foo", screen="dashboard"
    )
    assert local == Path(".specs/features/001-foo/baselines/dashboard.png")


def test_detect_link_capability_returns_symlink_on_posix(tmp_path: Path) -> None:
    assert detect_link_capability(tmp_path) == "symlink"


def test_write_and_read_link_mode_round_trip(tmp_path: Path) -> None:
    target = write_link_mode(tmp_path, "manifest")
    assert target.read_text(encoding="utf-8").strip() == "manifest"
    assert read_link_mode(tmp_path) == "manifest"


def test_read_link_mode_returns_none_when_invalid(tmp_path: Path) -> None:
    (tmp_path / ".specs" / "design").mkdir(parents=True)
    (tmp_path / ".specs" / "design" / ".link-mode").write_text("nonsense\n")
    assert read_link_mode(tmp_path) is None


def test_check_link_accepts_valid_relative_symlink(tmp_path: Path) -> None:
    registry_rel = Path(".specs/design/baselines/foo/web/home.png")
    registry_abs = tmp_path / registry_rel
    _make_png(registry_abs)
    local_abs = tmp_path / ".specs/features/foo/baselines/home.png"
    local_abs.parent.mkdir(parents=True, exist_ok=True)
    # Relative symlink:
    rel_target = Path("..") / ".." / ".." / "design" / "baselines" / "foo" / "web" / "home.png"
    os.symlink(rel_target, local_abs)

    result = check_link(
        feature_local_path=local_abs,
        expected_registry_path=registry_rel,
        project_root=tmp_path,
        feature_slug="foo",
        target="web",
        screen="home",
    )
    assert result is None


def test_check_link_flags_physical_copy(tmp_path: Path) -> None:
    registry_rel = Path(".specs/design/baselines/foo/web/home.png")
    _make_png(tmp_path / registry_rel)
    local_abs = tmp_path / ".specs/features/foo/baselines/home.png"
    _make_png(local_abs, b"copy-bytes")

    result = check_link(
        feature_local_path=local_abs,
        expected_registry_path=registry_rel,
        project_root=tmp_path,
        feature_slug="foo",
        target="web",
        screen="home",
    )
    assert isinstance(result, LinkViolation)
    assert result.kind == "physical_copy_where_link_required"


def test_check_link_flags_broken_symlink(tmp_path: Path) -> None:
    registry_rel = Path(".specs/design/baselines/foo/web/home.png")
    local_abs = tmp_path / ".specs/features/foo/baselines/home.png"
    local_abs.parent.mkdir(parents=True, exist_ok=True)
    os.symlink("does-not-exist.png", local_abs)

    result = check_link(
        feature_local_path=local_abs,
        expected_registry_path=registry_rel,
        project_root=tmp_path,
        feature_slug="foo",
        target="web",
        screen="home",
    )
    assert isinstance(result, LinkViolation)
    assert result.kind == "broken_symlink"


def test_check_link_returns_none_when_local_path_absent(tmp_path: Path) -> None:
    registry_rel = Path(".specs/design/baselines/foo/web/home.png")
    local_abs = tmp_path / ".specs/features/foo/baselines/missing.png"
    assert (
        check_link(
            feature_local_path=local_abs,
            expected_registry_path=registry_rel,
            project_root=tmp_path,
            feature_slug="foo",
            target="web",
            screen="missing",
        )
        is None
    )


def test_is_runtime_capture_misplaced_true_on_hash_collision(tmp_path: Path) -> None:
    payload = b"identical-png"
    misplaced = tmp_path / ".specs/design/screens/foo/dashboard.png"
    baseline = tmp_path / ".specs/design/baselines/foo/web/dashboard.png"
    _make_png(misplaced, payload)
    _make_png(baseline, payload)
    registry_root = tmp_path / ".specs/design/baselines/foo"

    assert is_runtime_capture_misplaced(
        candidate=misplaced, registry_baselines_dir=registry_root
    )


def test_is_runtime_capture_misplaced_false_when_no_collision(tmp_path: Path) -> None:
    misplaced = tmp_path / ".specs/design/screens/foo/dashboard.png"
    baseline = tmp_path / ".specs/design/baselines/foo/web/dashboard.png"
    _make_png(misplaced, b"design-bytes")
    _make_png(baseline, b"runtime-bytes")
    registry_root = tmp_path / ".specs/design/baselines/foo"

    assert not is_runtime_capture_misplaced(
        candidate=misplaced, registry_baselines_dir=registry_root
    )


def test_find_runtime_misplaced_lists_all_collisions(tmp_path: Path) -> None:
    payload = b"shared-payload"
    misplaced_a = tmp_path / ".specs/design/screens/foo/a.png"
    misplaced_b = tmp_path / ".specs/design/screens/foo/b.png"
    baseline = tmp_path / ".specs/design/baselines/foo/web/a.png"
    _make_png(misplaced_a, payload)
    _make_png(misplaced_b, payload)
    _make_png(baseline, payload)

    misplaced = find_runtime_misplaced_under_design_screens(
        project_root=tmp_path, feature_slug="foo"
    )
    assert set(misplaced) == {misplaced_a, misplaced_b}


def test_validate_manifest_returns_not_found_when_absent(tmp_path: Path) -> None:
    status, violations = validate_manifest(
        manifest_path=tmp_path / "missing.yml",
        project_root=tmp_path,
        feature_slug="foo",
        target="web",
    )
    assert status.found is False
    assert violations == []


def test_validate_manifest_flags_sha_mismatch_and_missing_registry(
    tmp_path: Path,
) -> None:
    registry_rel = Path(".specs/design/baselines/foo/web/home.png")
    _make_png(tmp_path / registry_rel, b"actual-bytes")
    manifest_path = tmp_path / ".specs/features/foo/baselines/baseline.manifest.yml"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "feature_slug": "foo",
        "target": "web",
        "entries": [
            {
                "screen": "home",
                "kind": "ref",
                "registry_path": str(registry_rel),
                "sha256": "abc123",  # deliberately wrong
            },
            {
                "screen": "missing",
                "kind": "ref",
                "registry_path": ".specs/design/baselines/foo/web/missing.png",
                "sha256": None,
            },
        ],
    }
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    manifest_json = manifest_path.with_suffix(".json")
    manifest_path.replace(manifest_json)

    status, violations = validate_manifest(
        manifest_path=manifest_json,
        project_root=tmp_path,
        feature_slug="foo",
        target="web",
    )
    assert status.found is True
    kinds = {v.kind for v in violations}
    assert "manifest_sha_mismatch" in kinds
    assert "registry_path_missing" in kinds


def test_sha256_of_returns_lowercase_hex(tmp_path: Path) -> None:
    target = tmp_path / "x.bin"
    target.write_bytes(b"abc")
    digest = sha256_of(target)
    assert digest == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
