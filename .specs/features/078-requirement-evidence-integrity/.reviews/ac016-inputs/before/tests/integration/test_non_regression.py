"""Level 3B — Non-regression tests: run /spec-specify N times, verify structural stability."""

from __future__ import annotations

import os
import re
from pathlib import Path

import anyio
import pytest

from tests.integration.helpers.sdk_runner import run_livespec_command

FIXTURES = Path(__file__).parent / "fixtures"

# Structural invariants — independent of generated content
STRUCTURAL_INVARIANTS = [
    ("frontmatter_yaml", lambda c: bool(re.match(r"^---\n.*\n---", c, re.DOTALL))),
    ("has_ac_section", lambda c: "Acceptance Criteria" in c),
    ("has_fr_section", lambda c: "Functional Requirements" in c),
    ("has_gherkin", lambda c: "```gherkin" in c),
    ("has_mermaid", lambda c: "```mermaid" in c),
    ("no_decision_needed", lambda c: "[DECISION NEEDED]" not in c.upper()),
    ("ac_sequential", lambda c: _check_sequential(re.findall(r"AC-(\d{3})", c))),
    ("fr_sequential", lambda c: _check_sequential(re.findall(r"FR-(\d{3})", c))),
]


def _check_sequential(numbers: list[str]) -> bool:
    expected = [f"{i + 1:03d}" for i in range(len(numbers))]
    return numbers == expected


@pytest.mark.level_3b
@pytest.mark.slow
@pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set",
)
class TestNonRegression:
    """
    Run the same command N times and verify invariant stability.
    Detects regressions caused by model updates.
    """

    N_RUNS = 3  # Minimal viable count — each run costs ~$3-5
    COMMAND = '/spec-specify "User can reset their password via email" --auto'

    def test_invariants_stable_across_n_runs(self):
        """
        Structural invariants must be satisfied in 100% of runs.
        Threshold is strict because all invariants are binary and deterministic;
        only content varies, not structure.
        """
        results = []
        for i in range(self.N_RUNS):
            result = anyio.run(
                run_livespec_command,
                self.COMMAND,
                "post-init",
                FIXTURES,
            )
            assert result.success, f"Run {i + 1} failed: {result.error}"

            # Find the generated spec.md
            specs = result.cwd / ".specs/features"
            feature_dirs = sorted(specs.glob("0*-*/"))
            assert feature_dirs, f"Run {i + 1}: no feature directory"
            spec_content = (feature_dirs[-1] / "spec.md").read_text()

            run_results = {}
            for invariant_name, check_fn in STRUCTURAL_INVARIANTS:
                run_results[invariant_name] = check_fn(spec_content)
            results.append(run_results)

        # Stability report
        failures = []
        for invariant_name, _ in STRUCTURAL_INVARIANTS:
            pass_count = sum(1 for r in results if r[invariant_name])
            if pass_count < self.N_RUNS:
                failures.append(f"{invariant_name}: {pass_count}/{self.N_RUNS} runs OK")

        assert not failures, "Unstable invariants (potential model regression):\n" + "\n".join(
            f"  - {f}" for f in failures
        )
