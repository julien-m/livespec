"""Level 3B + chaos — Tests on broken fixtures for graceful degradation."""

from __future__ import annotations

import os
from pathlib import Path

import anyio
import pytest

from tests.integration.helpers.sdk_runner import run_livespec_command

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.mark.chaos
@pytest.mark.level_3b
@pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set",
)
class TestChaosEngineering:
    """
    Verify that LiveSpec commands handle broken fixtures gracefully.
    The criterion is not "it works" but "it fails clearly or self-repairs".
    """

    def test_specify_without_specs_dir_suggests_init(self):
        """Without .specs/, /spec-specify must suggest /spec-init."""
        result = anyio.run(
            run_livespec_command,
            '/spec-specify "test feature"',
            "broken/no-specs-dir",
            FIXTURES,
        )
        combined_output = " ".join(result.stdout_messages).lower()
        # Command may fail (expected) but must mention spec.init
        assert "spec.init" in combined_output, (
            "Command did not suggest /spec-init when .specs/ is missing"
        )

    def test_specify_without_roadmap_does_not_crash(self):
        """Without roadmap.md, /spec-specify must not raise an unhandled exception."""
        result = anyio.run(
            run_livespec_command,
            '/spec-specify "feature without roadmap" --auto',
            "broken/missing-roadmap",
            FIXTURES,
        )
        # Either it creates the roadmap or stops cleanly
        # What is NOT acceptable: an uncaught Python exception
        assert result.error is None or "roadmap" in (result.error or "").lower(), (
            f"Unexpected error (unrelated to roadmap): {result.error}"
        )

    def test_init_on_existing_project_does_not_erase(self):
        """
        /spec-init on an already-initialized project must not erase
        existing specs.
        """
        result = anyio.run(
            run_livespec_command,
            "/spec-init",
            "post-init",  # already initialized
            FIXTURES,
        )
        # Existing files must still be there
        specs = result.cwd / ".specs"
        assert (specs / "project.md").exists(), "project.md erased by re-init"
        existing_content = (specs / "project.md").read_text()
        assert len(existing_content) > 100, "project.md appears to have been emptied"
