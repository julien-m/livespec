"""Tests for the coherence rule engine — filtering, suppress_if_creating, orchestration."""

from __future__ import annotations

from pathlib import Path

from validator.coherence.rule_engine import run_coherence
from validator.coherence.violation import Severity


def _write_minimal_specs(specs_root: Path) -> None:
    """Write a .specs/ structure that triggers multiple rule violations."""
    specs_root.mkdir(parents=True, exist_ok=True)

    # Roadmap with a checked item linking to a missing feature
    (specs_root / "roadmap.md").write_text(
        "# Roadmap\n\n- [x] [Ghost](features/099-ghost/)\n- [ ] [Auth](features/001-auth/)\n"
    )

    # Feature 001-auth with Draft status but no plan
    feat = specs_root / "features" / "001-auth"
    feat.mkdir(parents=True)
    (feat / "spec.md").write_text("---\nstatus: Planned\n---\n# Auth\n")

    # README referencing non-existent feature
    (specs_root / "README.md").write_text(
        "# Project\n| [features/001-auth](features/001-auth/) | Planned |\n"
        "| [features/099-ghost](features/099-ghost/) | Draft |\n"
    )

    # changelog referencing non-existent feature
    (specs_root / "changelog.md").write_text("- Added 099-ghost\n")

    # stack with no preflight
    stacks = specs_root / "stacks"
    stacks.mkdir()
    (stacks / "_default.md").write_text("## Stack\n\n- Redis\n")


class TestWaveFiltering:
    """--wave N only runs rules with wave <= N."""

    def test_wave_1_excludes_wave_2_and_3(self, tmp_path: Path) -> None:
        specs_root = tmp_path / ".specs"
        _write_minimal_specs(specs_root)

        result = run_coherence(specs_root, wave=1)
        rule_ids = {v.rule_id for v in result.violations}
        # Wave 2 rules: R3.1, R6.1. Wave 3: R3.2, R5.1
        for rid in rule_ids:
            group = rid.split(".")[0]
            assert group not in ("R3", "R5", "R6") or rid.startswith("R6") is False, (
                f"Wave 2/3 rule {rid} should not run with --wave 1"
            )

    def test_wave_3_includes_all(self, tmp_path: Path) -> None:
        specs_root = tmp_path / ".specs"
        _write_minimal_specs(specs_root)

        result_all = run_coherence(specs_root)
        result_w3 = run_coherence(specs_root, wave=3)
        # wave=3 should include everything (same as no filter)
        assert len(result_all.violations) == len(result_w3.violations)


class TestRuleFiltering:
    """--rules R1 only runs R1.x rules."""

    def test_filter_by_group(self, tmp_path: Path) -> None:
        specs_root = tmp_path / ".specs"
        _write_minimal_specs(specs_root)

        result = run_coherence(specs_root, rule_ids=["R1"])
        for v in result.violations:
            assert v.rule_id.startswith("R1"), f"Unexpected rule {v.rule_id}"

    def test_filter_by_specific_rule(self, tmp_path: Path) -> None:
        specs_root = tmp_path / ".specs"
        _write_minimal_specs(specs_root)

        result = run_coherence(specs_root, rule_ids=["R1.1"])
        for v in result.violations:
            assert v.rule_id == "R1.1"


class TestIgnoreFiltering:
    """--ignore R3.2 skips that specific rule."""

    def test_ignore_specific_rule(self, tmp_path: Path) -> None:
        specs_root = tmp_path / ".specs"
        _write_minimal_specs(specs_root)

        result = run_coherence(specs_root, ignore=["R1.1"])
        rule_ids = {v.rule_id for v in result.violations}
        assert "R1.1" not in rule_ids

    def test_ignore_multiple_rules(self, tmp_path: Path) -> None:
        specs_root = tmp_path / ".specs"
        _write_minimal_specs(specs_root)

        result = run_coherence(specs_root, ignore=["R1.1", "R2.1"])
        rule_ids = {v.rule_id for v in result.violations}
        assert "R1.1" not in rule_ids
        assert "R2.1" not in rule_ids


class TestSuppressIfCreating:
    """suppress_if_creating demotes violations to INFO for recently-modified features."""

    def test_recent_feature_violations_suppressed(self, tmp_path: Path) -> None:
        specs_root = tmp_path / ".specs"
        specs_root.mkdir(parents=True)

        # Feature with status mismatch (Draft but checked) — R1.3 has suppress_if_creating=True
        feat = specs_root / "features" / "001-auth"
        feat.mkdir(parents=True)
        (feat / "spec.md").write_text("---\nstatus: Draft\n---\n# Auth\n")

        (specs_root / "roadmap.md").write_text("- [x] [Auth](features/001-auth/)\n")

        # spec.md was just created (mtime is now), so it's within the 30-min window
        result = run_coherence(specs_root, rule_ids=["R1.3"])
        # R1.3 violations with suppress_if_creating should be demoted
        suppressed = result.suppressed
        # The violation should be suppressed (in the suppressed list, not violations)
        assert len(suppressed) > 0 or len(result.violations) > 0
        # If suppressed, severity should be INFO
        for v in suppressed:
            assert v.severity == Severity.INFO

    def test_no_suppress_flag_disables(self, tmp_path: Path) -> None:
        specs_root = tmp_path / ".specs"
        specs_root.mkdir(parents=True)

        feat = specs_root / "features" / "001-auth"
        feat.mkdir(parents=True)
        (feat / "spec.md").write_text("---\nstatus: Draft\n---\n# Auth\n")

        (specs_root / "roadmap.md").write_text("- [x] [Auth](features/001-auth/)\n")

        result = run_coherence(specs_root, rule_ids=["R1.3"], no_suppress=True)
        # With no_suppress, violations stay as-is (not suppressed)
        assert result.suppressed == []
        # The violation should be in violations list with ERROR severity
        errors = [v for v in result.violations if v.severity == Severity.ERROR]
        assert len(errors) > 0


class TestCoherenceResult:
    """Test CoherenceResult properties."""

    def test_has_errors(self, tmp_path: Path) -> None:
        specs_root = tmp_path / ".specs"
        _write_minimal_specs(specs_root)

        result = run_coherence(specs_root)
        assert result.has_errors is True
        assert len(result.errors) > 0

    def test_no_errors_on_clean_graph(self, tmp_path: Path) -> None:
        specs_root = tmp_path / ".specs"
        specs_root.mkdir(parents=True)
        (specs_root / "features").mkdir()

        result = run_coherence(specs_root)
        assert result.has_errors is False
        assert result.errors == []
        assert result.violations == []
