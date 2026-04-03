"""Session-level fixtures and configuration for LiveSpec integration tests."""

import json
import os
from pathlib import Path

import pytest

from tests.integration.helpers.cost_tracker import CostTracker


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "level_3a: tests without LLM, on static fixtures")
    config.addinivalue_line("markers", "level_3b: tests with SDK, isolated commands")
    config.addinivalue_line("markers", "level_3c: tests full end-to-end pipeline")
    config.addinivalue_line("markers", "chaos: chaos engineering tests on broken fixtures")
    config.addinivalue_line("markers", "slow: tests taking more than 30 seconds")


def pytest_collection_modifyitems(config, items):
    """Skip tests based on LIVESPEC_TEST_LEVEL environment variable."""
    level = os.environ.get("LIVESPEC_TEST_LEVEL", "3A").upper()

    level_markers = {
        "3A": {"level_3a"},
        "3B": {"level_3a", "level_3b", "chaos"},
        "3C": {"level_3a", "level_3b", "level_3c", "chaos"},
    }

    allowed = level_markers.get(level, {"level_3a"})

    for item in items:
        item_markers = {m.name for m in item.iter_markers()}
        level_marks = item_markers & {"level_3a", "level_3b", "level_3c", "chaos"}

        # If the test has no level marker, always run it
        if not level_marks:
            continue

        # If none of the test's level markers are in the allowed set, skip it
        if not (level_marks & allowed):
            item.add_marker(pytest.mark.skip(
                reason=f"Test level {level_marks} not included in LIVESPEC_TEST_LEVEL={level}"
            ))


@pytest.fixture(scope="session")
def fixtures_dir() -> Path:
    """Path to the integration test fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session", autouse=True)
def budget_guard():
    """
    Session-scoped budget guard that tracks cumulative cost across all tests.
    Auto-stops at 90% of LIVESPEC_TEST_BUDGET_USD.
    """
    limit = float(os.environ.get("LIVESPEC_TEST_BUDGET_USD", "25.0"))
    tracker = CostTracker(limit_usd=limit)
    yield tracker

    # Print cost report at the end of the session
    report = tracker.report()
    print("\n--- LiveSpec Test Cost Report ---")
    print(json.dumps(report, indent=2))
    print(f"Total: ${report['total_usd']:.4f} / ${report['limit_usd']:.2f}")
