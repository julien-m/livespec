"""Level 3B — Integration tests for /spec.specify via SDK."""

from __future__ import annotations

import os
import re
from pathlib import Path

import anyio
import pytest
import yaml

from tests.integration.helpers.sdk_runner import run_livespec_command

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.mark.level_3b
@pytest.mark.slow
@pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set",
)
class TestSpecSpecify:
    """Integration tests for /spec.specify on post-init fixture."""

    FEATURE_REQUEST = '/spec.specify "User can log in with email and password" --auto'

    @pytest.fixture(scope="class")
    def run_result(self):
        return anyio.run(
            run_livespec_command,
            self.FEATURE_REQUEST,
            "post-init",
            FIXTURES,
        )

    @pytest.fixture(scope="class")
    def spec_md_content(self, run_result) -> str:
        specs = run_result.cwd / ".specs/features"
        feature_dirs = list(specs.glob("0*-*/")) if specs.exists() else []
        assert len(feature_dirs) >= 1, "No feature directory created"
        # Take the most recent
        feature_dir = sorted(feature_dirs)[-1]
        spec_path = feature_dir / "spec.md"
        assert spec_path.exists(), f"spec.md missing in {feature_dir.name}"
        return spec_path.read_text()

    # --- Property-based invariants ---

    def test_frontmatter_yaml_valid(self, spec_md_content: str):
        """Invariant P1: frontmatter YAML parseable without error."""
        match = re.match(r"^---\n(.*?)\n---", spec_md_content, re.DOTALL)
        assert match, "No YAML frontmatter delimited by ---"
        try:
            data = yaml.safe_load(match.group(1))
        except yaml.YAMLError as e:
            pytest.fail(f"Invalid YAML in frontmatter: {e}")
        assert isinstance(data, dict), "Frontmatter must be a YAML object"

    def test_required_sections(self, spec_md_content: str):
        required = [
            "User Scenarios",
            "Acceptance Criteria",
            "Functional Requirements",
            "Key Entities",
            "Edge Cases",
            "Success Criteria",
        ]
        for section in required:
            assert section in spec_md_content, f"Required section missing: {section}"

    def test_gherkin_blocks_present(self, spec_md_content: str):
        """Invariant: at least 2 ```gherkin blocks with Feature: and Scenario:."""
        gherkin_blocks = re.findall(r"```gherkin\n(.*?)```", spec_md_content, re.DOTALL)
        assert len(gherkin_blocks) >= 2, f"Only {len(gherkin_blocks)} Gherkin block(s) (min: 2)"
        for block in gherkin_blocks:
            assert "Feature:" in block, "Gherkin block without 'Feature:'"
            assert "Scenario:" in block, "Gherkin block without 'Scenario:'"
            assert "Given" in block or "When" in block, "Gherkin block without Given/When"

    def test_mermaid_flowcharts_present(self, spec_md_content: str):
        """Invariant: at least one Mermaid flowchart per story."""
        flowcharts = re.findall(r"```mermaid\s*\nflowchart", spec_md_content)
        # Expect at least as many flowcharts as P1/P2 stories
        stories = re.findall(r"### Story \d+", spec_md_content)
        assert len(flowcharts) >= len(stories), (
            f"{len(flowcharts)} flowchart(s) for {len(stories)} story(ies)"
        )

    def test_ac_numbered_sequentially(self, spec_md_content: str):
        ac = re.findall(r"AC-(\d{3})", spec_md_content)
        expected = [f"{i + 1:03d}" for i in range(len(ac))]
        assert ac == expected, f"Non-sequential ACs: {ac}"

    def test_fr_numbered_sequentially(self, spec_md_content: str):
        fr = re.findall(r"FR-(\d{3})", spec_md_content)
        expected = [f"{i + 1:03d}" for i in range(len(fr))]
        assert fr == expected, f"Non-sequential FRs: {fr}"

    def test_at_least_5_ac(self, spec_md_content: str):
        ac = re.findall(r"AC-\d{3}", spec_md_content)
        assert len(ac) >= 5, f"Only {len(ac)} ACs (min: 5)"

    def test_no_decision_needed(self, spec_md_content: str):
        assert "[DECISION NEEDED]" not in spec_md_content.upper()

    def test_roadmap_updated(self, run_result):
        """Roadmap must have a checked item after /spec.specify."""
        roadmap = (run_result.cwd / ".specs/roadmap.md").read_text()
        checked_items = re.findall(r"- \[x\]", roadmap)
        assert len(checked_items) >= 1, "No checked item in roadmap.md"

    def test_readme_updated(self, run_result):
        """README must have a line in the features table."""
        readme = (run_result.cwd / ".specs/README.md").read_text()
        # Verify there is at least one line in the features section
        match = re.search(
            r"<!-- readme:features:start -->(.*?)<!-- readme:features:end -->",
            readme,
            re.DOTALL,
        )
        assert match, "Features section not found in README"
        assert "|" in match.group(1), "No line in features table"

    def test_changelog_feature_present(self, run_result):
        """Feature changelog must exist with at least one entry."""
        specs = run_result.cwd / ".specs/features"
        feature_dirs = sorted(specs.glob("0*-*/"))
        assert len(feature_dirs) >= 1
        changelog = feature_dirs[-1] / "changelog.md"
        assert changelog.exists(), "changelog.md missing in feature directory"
        content = changelog.read_text()
        assert "Spec" in content or "spec" in content, "No Spec-type entry in changelog"
