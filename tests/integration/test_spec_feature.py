"""Level 3C — End-to-end pipeline tests for /spec.feature via SDK."""

from __future__ import annotations

import os
import re
from pathlib import Path

import anyio
import pytest

from tests.integration.helpers.sdk_runner import run_livespec_command

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.mark.level_3c
@pytest.mark.slow
@pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set",
)
class TestSpecFeaturePipeline:
    """
    End-to-end test: /spec.feature generates spec.md + plan.md
    and both are structurally coherent.
    """

    COMMAND = '/spec.feature "User can view their account dashboard" --auto'

    @pytest.fixture(scope="class")
    def run_result(self):
        return anyio.run(
            run_livespec_command,
            self.COMMAND,
            "post-init",
            FIXTURES,
            timeout_sec=240,  # longer pipeline
            max_turns=80,
        )

    @pytest.fixture(scope="class")
    def feature_dir(self, run_result) -> Path:
        specs = run_result.cwd / ".specs/features"
        dirs = sorted(specs.glob("0*-*/"))
        assert dirs, "No feature created"
        return dirs[-1]

    def test_spec_md_generated(self, feature_dir):
        assert (feature_dir / "spec.md").exists()

    def test_plan_md_generated(self, feature_dir):
        assert (feature_dir / "plan.md").exists()

    def test_plan_md_required_sections(self, feature_dir):
        plan = (feature_dir / "plan.md").read_text()
        required = [
            "Summary",
            "Technical Context",
            "Constitution Check",
            "Implementation Plan",
            "Testing Strategy",
        ]
        for section in required:
            assert section in plan, f"Missing plan.md section: {section}"

    def test_plan_md_has_mermaid_sequence_or_state(self, feature_dir):
        plan = (feature_dir / "plan.md").read_text()
        has_sequence = "sequenceDiagram" in plan
        has_state = "stateDiagram" in plan
        has_er = "erDiagram" in plan
        assert has_sequence or has_state or has_er, (
            "plan.md must have at least one Mermaid diagram "
            "(sequenceDiagram, stateDiagram, or erDiagram)"
        )

    def test_fr_coherence_spec_plan(self, feature_dir):
        """FRs in spec.md must be referenced in plan.md."""
        spec = (feature_dir / "spec.md").read_text()
        plan = (feature_dir / "plan.md").read_text()

        spec_frs = set(re.findall(r"FR-\d{3}", spec))
        plan_frs = set(re.findall(r"FR-\d{3}", plan))

        uncovered = spec_frs - plan_frs
        # Tolerate partial plan but require at least 80% FR coverage
        if spec_frs:
            coverage = len(spec_frs & plan_frs) / len(spec_frs)
            assert coverage >= 0.8, (
                f"Insufficient FR spec->plan coverage: {coverage:.0%} (uncovered: {uncovered})"
            )

    def test_changelog_global_updated(self, run_result):
        changelog = (run_result.cwd / ".specs/changelog.md").read_text()
        assert len(changelog.strip()) > 0, "Global changelog.md is empty"
