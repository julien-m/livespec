"""Regression tests for mandatory visual certification during implementation.

# @spec FR-006: Regression tests
#   — .specs/features/046-visual-implementation-gate/spec.md#fr-006
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_implement_requires_visual_gate_before_final_status() -> None:
    """AC-001/AC-002: UI features run /spec-test --visual before finalization."""
    body = _read(".agent-sync/skills/spec-implement/SKILL.md")

    assert "Phase 6.5 — Mandatory Visual Gate" in body
    assert "/spec-test <feature> --auto --visual" in body
    assert "before Phase 7" in body
    assert "before Phase 8.5" in body
    assert "Visual Gate Verdict: PASS" in body


def test_visual_tooling_failure_blocks_implementation() -> None:
    """AC-003: unavailable visual tooling cannot silently pass UI features."""
    body = _read(".agent-sync/skills/spec-implement/SKILL.md")

    assert "Visual tooling unavailable on a UI feature is BLOCKED" in body
    assert "do not continue without blocking" in body
    assert "status remains `In Progress`" in body
    old_skip_message = (
        'Visual baselines skipped — Playwright not installed" and continue without blocking'
    )
    assert old_skip_message not in body


def test_no_visual_flag_caps_ui_feature_at_in_progress() -> None:
    """AC-004: --no-visual is allowed for partial work only."""
    body = _read(".agent-sync/skills/spec-implement/SKILL.md")

    assert "`--no-visual` on a visual feature" in body
    assert "must set Status to `In Progress`" in body
    assert "never `Implemented`" in body


def test_spec_test_exposes_structured_visual_gate_verdict() -> None:
    """AC-005: /spec-test provides a verdict consumable by /spec-implement."""
    body = _read(".agent-sync/skills/spec-test/SKILL.md")

    assert "### Visual Gate Verdict" in body
    assert "PASS | FAIL | BLOCKED" in body
    assert "Consumed by `/spec-implement` Phase 6.5" in body
    assert "exit code 0 only for PASS" in body


def test_expectations_contracts_describe_visual_gate() -> None:
    """AC-006: command expectation contracts stay aligned with visual gating."""
    implement = _read(".agent-sync/skills/spec-implement/expectations.md")
    test = _read(".agent-sync/skills/spec-test/expectations.md")

    assert "Visual Gate Verdict" in implement
    assert "/spec-test <feature> --auto --visual" in implement
    assert "visual gate passed before final status" in implement

    assert "Visual Gate Verdict" in test
    assert "PASS | FAIL | BLOCKED" in test


# ---------------------------------------------------------------------------
# Broken-variant regression suite (visual-gate-fix cycle, Phase 4 step 1).
# Each variant simulates one observable failure mode the gate must catch.
# ---------------------------------------------------------------------------


def _setup_minimal_visual_feature(project_root: Path, slug: str) -> Path:
    """Seed a project root with a VISUAL feature carrying registry artefacts."""
    feature_dir = project_root / ".specs" / "features" / slug
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "spec.md").write_text(
        "---\nvisual: true\nsurface: web\n---\n# Spec\n",
        encoding="utf-8",
    )
    # Strong signal s2: design/screens entry.
    screen_png = project_root / ".specs" / "design" / "screens" / slug / "dash.png"
    screen_png.parent.mkdir(parents=True, exist_ok=True)
    screen_png.write_bytes(b"mockup-png")
    # Approved baseline registry.
    baseline = (
        project_root / ".specs" / "design" / "baselines" / slug / "web" / "dash.png"
    )
    baseline.parent.mkdir(parents=True, exist_ok=True)
    baseline.write_bytes(b"approved-baseline")
    return feature_dir


def test_variant_missing_mockup_blocks_gate(tmp_path: Path) -> None:
    """Missing entry under `.specs/design/screens/<slug>/` → CONFLICT/BLOCKED."""
    from validator.visual_gate import validate_gate

    slug = "vbm-missing-mockup"
    feature_dir = tmp_path / ".specs" / "features" / slug
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "spec.md").write_text(
        "---\nvisual: true\n---\n# Spec\n", encoding="utf-8"
    )
    report = validate_gate(
        project_root=tmp_path,
        feature_slug=slug,
        command="spec-check",
        target="web",
        strict_links=True,
    )
    assert report.verdict == "BLOCKED"
    assert report.conflict_reason == "spec_declares_visual_but_no_artifacts"


def test_variant_missing_baseline_manifest_target_dir_blocks_gate(
    tmp_path: Path,
) -> None:
    """`.specs/design/baselines/<slug>/<target>/` absent → BLOCKED missing_artifacts."""
    from validator.visual_gate import validate_gate

    slug = "vbm-no-baseline-target"
    feature_dir = tmp_path / ".specs" / "features" / slug
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "spec.md").write_text(
        "---\nvisual: true\n---\n# Spec\n", encoding="utf-8"
    )
    screen_png = tmp_path / ".specs" / "design" / "screens" / slug / "dash.png"
    screen_png.parent.mkdir(parents=True, exist_ok=True)
    screen_png.write_bytes(b"mockup")
    report = validate_gate(
        project_root=tmp_path,
        feature_slug=slug,
        command="spec-check",
        target="web",
        strict_links=True,
    )
    assert report.verdict == "BLOCKED"
    assert any("baselines" in m for m in report.missing_artifacts)


def test_variant_runtime_under_design_screens_fails_gate(tmp_path: Path) -> None:
    """A runtime PNG whose sha256 matches a baseline registry entry → FAIL."""
    from validator.visual_gate import validate_gate

    slug = "vbm-runtime-misplaced"
    _setup_minimal_visual_feature(tmp_path, slug)
    # Overwrite the mockup with the SAME bytes as the approved baseline →
    # circular comparison.
    baseline_bytes = (
        tmp_path / ".specs/design/baselines" / slug / "web" / "dash.png"
    ).read_bytes()
    (tmp_path / ".specs/design/screens" / slug / "dash.png").write_bytes(
        baseline_bytes
    )
    report = validate_gate(
        project_root=tmp_path,
        feature_slug=slug,
        command="spec-check",
        target="web",
        strict_links=True,
    )
    assert report.verdict == "FAIL"
    assert report.runtime_in_design_screens_violations


def test_variant_physical_copy_instead_of_symlink_fails_gate(tmp_path: Path) -> None:
    """Plain PNG under `.specs/features/<slug>/baselines/` → FAIL link violation."""
    from validator.visual_gate import validate_gate

    slug = "vbm-physical-copy"
    _setup_minimal_visual_feature(tmp_path, slug)
    feature_local = (
        tmp_path / ".specs/features" / slug / "baselines" / "dash.png"
    )
    feature_local.parent.mkdir(parents=True, exist_ok=True)
    feature_local.write_bytes(b"physical-copy-not-symlink")
    report = validate_gate(
        project_root=tmp_path,
        feature_slug=slug,
        command="spec-check",
        target="web",
        strict_links=True,
    )
    assert report.verdict == "FAIL"
    assert any(
        v.kind == "physical_copy_where_link_required" for v in report.link_violations
    )


def test_variant_broken_symlink_in_feature_baselines_fails_gate(
    tmp_path: Path,
) -> None:
    """Symlink whose target is missing → manifest-driven FAIL/BLOCKED."""
    import json
    import os

    from validator.visual_gate import validate_gate

    slug = "vbm-broken-symlink"
    _setup_minimal_visual_feature(tmp_path, slug)
    feature_local = (
        tmp_path / ".specs/features" / slug / "baselines" / "dash.png"
    )
    feature_local.parent.mkdir(parents=True, exist_ok=True)
    os.symlink("does-not-exist.png", feature_local)
    # JSON is a valid YAML subset, so the production yaml.safe_load parses
    # this without needing a typed-yaml shim in the test.
    manifest = feature_local.parent / "baseline.manifest.yml"
    manifest.write_text(
        json.dumps(
            {
                "feature_slug": slug,
                "target": "web",
                "entries": [
                    {
                        "screen": "dash",
                        "kind": "symlink",
                        "registry_path": (
                            f".specs/design/baselines/{slug}/web/dash.png"
                        ),
                        "feature_local_path": (
                            f".specs/features/{slug}/baselines/dash.png"
                        ),
                        "sha256": None,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    report = validate_gate(
        project_root=tmp_path,
        feature_slug=slug,
        command="spec-check",
        target="web",
        strict_links=True,
    )
    assert report.verdict == "FAIL"
    assert any(v.kind == "broken_symlink" for v in report.link_violations)


def test_variant_missing_compare_report_blocks_gate(tmp_path: Path) -> None:
    """`design-alignment/<screen>/` exists but compare files missing → BLOCKED.

    Locks the strict gate behaviour added in the visual-gate-fix cycle: an
    incomplete `design-alignment/<screen>/` directory (no design-contract or
    runtime-contract) MUST surface as missing_artifacts so the gate goes
    BLOCKED instead of silently dropping the broken screen on the floor.
    """
    from validator.visual_gate import validate_gate

    slug = "vbm-no-compare-report"
    _setup_minimal_visual_feature(tmp_path, slug)
    # Create an INCOMPLETE design-alignment dir (no design/runtime contracts).
    alignment_dir = (
        tmp_path / ".specs/features" / slug / "design-alignment" / "dash"
    )
    alignment_dir.mkdir(parents=True, exist_ok=True)
    report = validate_gate(
        project_root=tmp_path,
        feature_slug=slug,
        command="spec-check",
        target="web",
        strict_links=True,
    )
    assert report.verdict == "BLOCKED"
    assert any(
        "design-contract.json" in m or "runtime-contract.json" in m
        for m in report.missing_artifacts
    )


def test_variant_compare_report_fail_propagates_to_gate(tmp_path: Path) -> None:
    """A design-alignment FAIL verdict propagates into the gate verdict."""
    import json

    from validator.visual_gate import validate_gate

    slug = "vbm-alignment-fail"
    _setup_minimal_visual_feature(tmp_path, slug)
    # Seed a design-alignment screen dir with contracts that will FAIL.
    screen_dir = (
        tmp_path / ".specs/features" / slug / "design-alignment" / "dash"
    )
    screen_dir.mkdir(parents=True, exist_ok=True)
    design = {
        "screen": "dash",
        "support": {
            "width": 1440,
            "height": 900,
            "dpr": 1,
            "orientation": "landscape",
            "shape": "rect",
            "safe_area_top": 0,
            "header_height": 0,
            "decorative_shell": False,
        },
        "nodes": [
            {"id": "n1", "name": "btn", "type": "button", "text": "Click"}
        ],
    }
    runtime_drift = {
        "screen": "dash",
        "support": design["support"],
        "nodes": [
            {"id": "n1", "name": "btn", "type": "button", "text": "Tap me"}
        ],
    }
    (screen_dir / "design-contract.json").write_text(
        json.dumps(design), encoding="utf-8"
    )
    (screen_dir / "runtime-contract.json").write_text(
        json.dumps(runtime_drift), encoding="utf-8"
    )
    report = validate_gate(
        project_root=tmp_path,
        feature_slug=slug,
        command="spec-check",
        target="web",
        strict_links=True,
    )
    assert report.verdict == "FAIL"
    assert any(r.verdict == "FAIL" for r in report.alignment)


def test_variant_command_output_claims_done_without_evidence_fails_gate(
    tmp_path: Path,
) -> None:
    """Spec marks the feature done but no real visual artefacts exist → BLOCKED."""
    from validator.visual_gate import validate_gate

    slug = "vbm-claims-done-no-evidence"
    feature_dir = tmp_path / ".specs" / "features" / slug
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "spec.md").write_text(
        "---\nvisual: true\nstatus: implemented\n---\n# Spec done\n",
        encoding="utf-8",
    )
    # implementation.md claiming everything passed.
    (feature_dir / "implementation.md").write_text(
        "All AC verified. Visual: PASS.\n", encoding="utf-8"
    )
    report = validate_gate(
        project_root=tmp_path,
        feature_slug=slug,
        command="spec-feature",
        target="web",
        strict_links=True,
    )
    assert report.verdict == "BLOCKED"
    assert report.conflict_reason == "spec_declares_visual_but_no_artifacts"


def test_variant_weak_signals_only_yields_conflict_blocked(tmp_path: Path) -> None:
    """Only weak signals (s5 baselines or s6 surfaces.yaml) → CONFLICT/BLOCKED."""
    from validator.visual_gate import validate_gate

    slug = "vbm-weak-only"
    feature_dir = tmp_path / ".specs" / "features" / slug
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "spec.md").write_text("# Spec\n", encoding="utf-8")
    # Only s5 (feature baselines plain file) — no s2/s3/s4.
    (feature_dir / "baselines").mkdir(parents=True, exist_ok=True)
    (feature_dir / "baselines" / "x.png").write_bytes(b"weak")
    report = validate_gate(
        project_root=tmp_path,
        feature_slug=slug,
        command="spec-check",
        target=None,
        strict_links=True,
    )
    assert report.verdict == "BLOCKED"
    assert report.conflict_reason is not None
    assert "weak_signals_only" in report.conflict_reason


# ---------------------------------------------------------------------------
# Shared-contract manifest fallback (no-copy invariant)
# ---------------------------------------------------------------------------


def _write_normalized_contract(path: Path, screen: str) -> None:
    import json as _json

    payload = {
        "screen": screen,
        "support": {
            "width": 1440,
            "height": 900,
            "dpr": 1,
            "orientation": "landscape",
            "shape": "rect",
            "safe_area_top": 0,
            "header_height": 0,
            "decorative_shell": False,
        },
        "nodes": [
            {"id": "n1", "name": "btn", "type": "button", "text": "Click"}
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_json.dumps(payload), encoding="utf-8")


def test_alignment_manifest_with_shared_sources_yields_pass(tmp_path: Path) -> None:
    """Screen dir carrying only ``design-alignment.manifest.json`` referencing
    shared normalized contracts under ``.specs/...`` → PASS (no-copy contract)."""
    import json as _json

    from validator.visual_gate import validate_gate

    slug = "vbm-shared-manifest"
    _setup_minimal_visual_feature(tmp_path, slug)
    alignment_root = (
        tmp_path / ".specs/features" / slug / "design-alignment"
    )
    shared_design = alignment_root / "normalized-design.json"
    shared_runtime = alignment_root / "normalized-runtime.json"
    _write_normalized_contract(shared_design, "dash")
    _write_normalized_contract(shared_runtime, "dash")

    screen_dir = alignment_root / "dash"
    screen_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "screen": "dash",
        "design_source": (
            f".specs/features/{slug}/design-alignment/normalized-design.json"
        ),
        "runtime_source": (
            f".specs/features/{slug}/design-alignment/normalized-runtime.json"
        ),
    }
    (screen_dir / "design-alignment.manifest.json").write_text(
        _json.dumps(manifest), encoding="utf-8"
    )

    report = validate_gate(
        project_root=tmp_path,
        feature_slug=slug,
        command="spec-check",
        target="web",
        strict_links=True,
    )
    assert report.verdict == "PASS", report.to_dict()
    assert any(r.screen == "dash" and r.verdict == "PASS" for r in report.alignment)
    # No physical copy was created in the screen dir.
    assert not (screen_dir / "design-contract.json").exists()
    assert not (screen_dir / "runtime-contract.json").exists()


def test_alignment_manifest_malformed_keeps_blocked(tmp_path: Path) -> None:
    """Manifest present but missing ``design_source``/``runtime_source`` →
    BLOCKED with explicit diagnostic in ``missing_artifacts``."""
    from validator.visual_gate import validate_gate

    slug = "vbm-manifest-malformed"
    _setup_minimal_visual_feature(tmp_path, slug)
    screen_dir = (
        tmp_path / ".specs/features" / slug / "design-alignment" / "dash"
    )
    screen_dir.mkdir(parents=True, exist_ok=True)
    (screen_dir / "design-alignment.manifest.json").write_text(
        '{"screen": "dash"}', encoding="utf-8"
    )

    report = validate_gate(
        project_root=tmp_path,
        feature_slug=slug,
        command="spec-check",
        target="web",
        strict_links=True,
    )
    assert report.verdict == "BLOCKED"
    assert any(
        "design_source" in m or "runtime_source" in m
        for m in report.missing_artifacts
    )


def test_alignment_manifest_unresolved_source_keeps_blocked(tmp_path: Path) -> None:
    """Manifest references a non-existent source → BLOCKED with the bad ref."""
    import json as _json

    from validator.visual_gate import validate_gate

    slug = "vbm-manifest-unresolved"
    _setup_minimal_visual_feature(tmp_path, slug)
    screen_dir = (
        tmp_path / ".specs/features" / slug / "design-alignment" / "dash"
    )
    screen_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "screen": "dash",
        "design_source": ".specs/does-not-exist/normalized-design.json",
        "runtime_source": ".specs/does-not-exist/normalized-runtime.json",
    }
    (screen_dir / "design-alignment.manifest.json").write_text(
        _json.dumps(manifest), encoding="utf-8"
    )

    report = validate_gate(
        project_root=tmp_path,
        feature_slug=slug,
        command="spec-check",
        target="web",
        strict_links=True,
    )
    assert report.verdict == "BLOCKED"
    assert any("unresolved" in m for m in report.missing_artifacts)
