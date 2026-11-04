"""The Visual Tests workflow runs on a runner image where Playwright can install browsers."""

# @spec FR-017: Each visual test runs per browser in CI
#   — .specs/features/010-visual-testing-complete/spec.md#fr-017

from pathlib import Path

import yaml

WORKFLOW = Path(__file__).resolve().parents[1] / ".github/workflows/visual-tests.yml"
# ubuntu-latest moved to 26.04, where the pinned Playwright cannot install browsers.
RUNNER_IMAGE = "ubuntu-24.04"


def test_visual_matrix_runs_on_a_runner_image_supported_by_playwright() -> None:
    """Every browser project of the matrix needs an image the pinned Playwright supports."""
    job = yaml.safe_load(WORKFLOW.read_text())["jobs"]["visual-tests"]
    assert job["runs-on"] == RUNNER_IMAGE
