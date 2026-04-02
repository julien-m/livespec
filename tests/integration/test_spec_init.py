"""Level 3B — Integration tests for /spec.init via SDK."""

from __future__ import annotations

import os
import re

import anyio
import pytest
from pathlib import Path
from tests.integration.helpers.sdk_runner import run_livespec_command
from tests.integration.helpers.assertions import (
    assert_specs_directory_valid,
    assert_file_exists,
    assert_roadmap_has_tiers,
    assert_adr_exists,
)

FIXTURES = Path(__file__).parent / "fixtures"
BUDGET_LIMIT_USD = float(os.environ.get("LIVESPEC_TEST_BUDGET_USD", "25"))


@pytest.mark.level_3b
@pytest.mark.slow
@pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set",
)
class TestSpecInit:
    """Integration tests for /spec.init on minimal-app fixture."""

    @pytest.fixture(scope="class")
    def run_result(self):
        """Run /spec.init once for all tests in this class."""
        result = anyio.run(
            run_livespec_command,
            "/spec.init",
            "minimal-app",
            FIXTURES,
        )
        assert result.estimated_cost_usd < BUDGET_LIMIT_USD / 5, (
            f"Cost too high: ${result.estimated_cost_usd:.2f} "
            f"(limit: ${BUDGET_LIMIT_USD / 5:.2f})"
        )
        return result

    def test_command_completes_without_error(self, run_result):
        assert run_result.error is None, f"SDK error: {run_result.error}"
        assert run_result.success, "Command did not terminate normally"

    def test_specs_directory_created(self, run_result):
        specs_dir = run_result.cwd / ".specs"
        assert specs_dir.exists(), ".specs/ was not created"

    def test_required_files_present(self, run_result):
        specs = run_result.cwd / ".specs"
        required = [
            "project.md",
            "constitution.md",
            "roadmap.md",
            "README.md",
            "preflight.md",
            "preflight-report.md",
            "stacks/_default.md",
            "testing/strategy.md",
        ]
        for f in required:
            assert (specs / f).exists(), f"Missing file: .specs/{f}"

    def test_at_least_one_adr_created(self, run_result):
        decisions = run_result.cwd / ".specs/stacks/decisions"
        adrs = list(decisions.glob("ADR-*.md")) if decisions.exists() else []
        assert len(adrs) >= 1, (
            "Quality gate /spec.init: at least 1 ADR required (BLOCKING)"
        )

    def test_roadmap_has_tiers_with_items(self, run_result):
        roadmap = run_result.cwd / ".specs/roadmap.md"
        content = roadmap.read_text()
        assert "<!-- roadmap:mvp:start -->" in content
        assert "<!-- roadmap:mvp:end -->" in content
        # At least one item in MVP tier
        mvp_match = re.search(
            r"<!-- roadmap:mvp:start -->(.*?)<!-- roadmap:mvp:end -->",
            content,
            re.DOTALL,
        )
        assert mvp_match, "MVP section not found"
        mvp_content = mvp_match.group(1)
        items = re.findall(r"^- \[", mvp_content, re.MULTILINE)
        assert len(items) >= 1, "MVP must contain at least 1 item"

    def test_project_md_without_placeholders(self, run_result):
        project = (run_result.cwd / ".specs/project.md").read_text()
        placeholders = ["[TBD]", "[PLACEHOLDER]", "[YOUR PROJECT]"]
        for p in placeholders:
            assert p not in project, (
                f"Unreplaced placeholder in project.md: {p}"
            )

    def test_stack_default_without_tbd(self, run_result):
        stack = (run_result.cwd / ".specs/stacks/_default.md").read_text()
        assert "[TBD]" not in stack, "_default.md still contains [TBD]"
