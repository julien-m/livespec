"""Tests for the coherence rule engine — filtering, suppress_if_creating, orchestration."""

from __future__ import annotations

import os
import time
from pathlib import Path

from validator.coherence.rule_engine import run_coherence
from validator.coherence.rules import get_rules
from validator.coherence.violation import Severity

_OLD_MTIME = time.time() - 2 * 60 * 60  # two hours: outside the 30-minute grace window


def _age(path: Path, mtime: float = _OLD_MTIME) -> None:
    os.utime(path, (mtime, mtime))


def _write_minimal_specs(specs_root: Path) -> None:
    """Write an aged .specs/ tree that triggers rules from waves 1, 2 and 3."""
    specs_root.mkdir(parents=True, exist_ok=True)

    # Roadmap with a checked item linking to a missing feature (R1.1)
    (specs_root / "roadmap.md").write_text(
        "# Roadmap\n\n- [x] [Ghost](features/099-ghost/)\n- [ ] [Auth](features/001-auth/)\n"
    )

    # Planned feature without plan.md (R2.1) and without changelog.md (R6.1, wave 2)
    feat = specs_root / "features" / "001-auth"
    feat.mkdir(parents=True)
    (feat / "spec.md").write_text("---\nstatus: Planned\n---\n# Auth\n")
    _age(feat / "spec.md")

    # README referencing a non-existent feature (R4.1)
    (specs_root / "README.md").write_text(
        "# Project\n| [features/001-auth](features/001-auth/) | Planned |\n"
        "| [features/099-ghost](features/099-ghost/) | Draft |\n"
    )
    (specs_root / "changelog.md").write_text("- Added 099-ghost\n")

    # Stack without preflight check (R5.1, wave 3)
    stacks = specs_root / "stacks"
    stacks.mkdir()
    (stacks / "_default.md").write_text("## Stack\n\n- Redis\n")


def _write_implemented_unchecked(specs_root: Path) -> Path:
    """Implemented feature whose roadmap item is unchecked (R1.3, suppressible)."""
    feat = specs_root / "features" / "001-auth"
    feat.mkdir(parents=True)
    (feat / "spec.md").write_text("---\nstatus: Implemented\n---\n# Auth\n")
    (specs_root / "roadmap.md").write_text("- [ ] [Auth](features/001-auth/)\n")
    return feat / "spec.md"


class TestWaveFiltering:
    """--wave N only runs rules with wave <= N."""

    def test_wave_1_excludes_later_waves(self, tmp_path: Path) -> None:
        specs_root = tmp_path / ".specs"
        _write_minimal_specs(specs_root)
        waves = {rule.rule_id: rule.wave for rule in get_rules()}

        all_ids = {v.rule_id for v in run_coherence(specs_root).violations}
        wave1_ids = {v.rule_id for v in run_coherence(specs_root, wave=1).violations}

        assert {"R6.1", "R5.1"} <= all_ids
        assert wave1_ids
        assert all(waves[rid] <= 1 for rid in wave1_ids)
        assert wave1_ids == {rid for rid in all_ids if waves[rid] <= 1}

    def test_wave_3_includes_waves_up_to_3(self, tmp_path: Path) -> None:
        specs_root = tmp_path / ".specs"
        _write_minimal_specs(specs_root)

        result_w3 = run_coherence(specs_root, wave=3)

        assert {"R1.1", "R6.1", "R5.1"} <= {v.rule_id for v in result_w3.violations}


class TestRuleFiltering:
    """--rules R1 only runs R1.x rules."""

    def test_filter_by_group(self, tmp_path: Path) -> None:
        specs_root = tmp_path / ".specs"
        _write_minimal_specs(specs_root)

        result = run_coherence(specs_root, rule_ids=["R1"])

        assert result.violations
        assert all(v.rule_id.startswith("R1.") for v in result.violations)

    def test_filter_by_specific_rule(self, tmp_path: Path) -> None:
        specs_root = tmp_path / ".specs"
        _write_minimal_specs(specs_root)

        result = run_coherence(specs_root, rule_ids=["R2.1"])

        assert [v.rule_id for v in result.violations] == ["R2.1"]


class TestIgnoreFiltering:
    """--ignore R1.1 skips that specific rule."""

    def test_ignore_multiple_rules(self, tmp_path: Path) -> None:
        specs_root = tmp_path / ".specs"
        _write_minimal_specs(specs_root)
        baseline = {v.rule_id for v in run_coherence(specs_root).violations}

        result = run_coherence(specs_root, ignore=["R1.1", "R2.1"])
        rule_ids = {v.rule_id for v in result.violations}

        assert {"R1.1", "R2.1"} <= baseline
        assert rule_ids == baseline - {"R1.1", "R2.1"}


class TestSuppressIfCreating:
    """suppress_if_creating demotes violations to INFO for recently-modified features."""

    def test_recent_feature_violation_is_demoted_to_info(self, tmp_path: Path) -> None:
        specs_root = tmp_path / ".specs"
        _write_implemented_unchecked(specs_root)  # spec.md mtime is now

        result = run_coherence(specs_root, rule_ids=["R1.3"])

        assert result.violations == []
        assert [v.rule_id for v in result.suppressed] == ["R1.3"]
        suppressed = result.suppressed[0]
        assert suppressed.severity == Severity.INFO
        assert suppressed.message.startswith("[in-progress, 0min] Feature '001-auth'")

    def test_old_feature_violation_is_not_suppressed(self, tmp_path: Path) -> None:
        specs_root = tmp_path / ".specs"
        _age(_write_implemented_unchecked(specs_root))

        result = run_coherence(specs_root, rule_ids=["R1.3"])

        assert result.suppressed == []
        assert [(v.rule_id, v.severity) for v in result.violations] == [("R1.3", Severity.ERROR)]
        assert not result.violations[0].message.startswith("[in-progress")

    def test_rule_without_suppression_flag_is_never_demoted(self, tmp_path: Path) -> None:
        specs_root = tmp_path / ".specs"
        feat = specs_root / "features" / "001-auth"
        feat.mkdir(parents=True)
        (feat / "spec.md").write_text("---\nstatus: Draft\n---\n# Auth\n")
        (feat / "implementation.md").write_text("# Implementation\n")

        result = run_coherence(specs_root, rule_ids=["R2.2"])

        assert result.suppressed == []
        assert [(v.rule_id, v.severity) for v in result.violations] == [("R2.2", Severity.WARNING)]

    def test_no_suppress_flag_disables(self, tmp_path: Path) -> None:
        specs_root = tmp_path / ".specs"
        _write_implemented_unchecked(specs_root)

        result = run_coherence(specs_root, rule_ids=["R1.3"], no_suppress=True)

        assert result.suppressed == []
        assert [(v.rule_id, v.severity) for v in result.violations] == [("R1.3", Severity.ERROR)]


class TestCoherenceResult:
    """Test CoherenceResult properties."""

    def test_has_errors(self, tmp_path: Path) -> None:
        specs_root = tmp_path / ".specs"
        _write_minimal_specs(specs_root)

        result = run_coherence(specs_root)

        assert result.has_errors is True
        assert {v.rule_id for v in result.errors} >= {"R1.1", "R2.1"}

    def test_no_errors_on_clean_graph(self, tmp_path: Path) -> None:
        specs_root = tmp_path / ".specs"
        specs_root.mkdir(parents=True)
        (specs_root / "features").mkdir()

        result = run_coherence(specs_root)

        assert result.has_errors is False
        assert result.violations == []
