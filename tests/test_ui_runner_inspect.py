"""Tests for the .xcresult inspector and Swift auto-patcher.

Covers:
  * `parse_tree_elements` extracts buttons/tabs/cells from XCUI debugDescription.
  * `rewrite_swift_candidates` updates `tapFirstAvailable`/`tapAnyTab` candidate
    lists with discovered labels, preserving method bodies and existing values.

# @spec FR-009: developer-friendly diagnostics — feature 030
"""

from __future__ import annotations

from pathlib import Path

from validator.ui_runner_inspect import parse_tree_elements, rewrite_swift_candidates

SAMPLE_TREE = """Application 0x600003700000, pid: 12345, label: 'STRAPT'
  Window 0x...
    TabBar 0x...
      Button 0x..., {{0, 0}, {100, 50}}, identifier: 'library_tab', label: 'Library'
      Button 0x..., {{100, 0}, {100, 50}}, identifier: 'history_tab', label: 'History'
      Button 0x..., {{200, 0}, {100, 50}}, label: 'Settings'
    Other 0x...
      NavigationBar 0x...
        Button 0x..., {{0, 0}, {44, 44}}, identifier: 'plus', label: 'Add Workout'
      Cell 0x..., {{0, 100}, {300, 60}}, identifier: 'workout_row_0'
        StaticText 0x..., label: 'Push Day'
"""


def test_parse_tree_elements_separates_tabs_from_buttons() -> None:
    inv = parse_tree_elements(SAMPLE_TREE)
    assert "Library" in inv["tabs"]
    assert "History" in inv["tabs"]
    assert "Settings" in inv["tabs"]
    # Tab identifiers also extracted
    assert "library_tab" in inv["tabs"]
    # NavBar button is NOT a tab
    assert "Add Workout" in inv["buttons"]
    assert "plus" in inv["buttons"]
    assert "Add Workout" not in inv["tabs"]


def test_parse_tree_elements_collects_cells_and_text() -> None:
    inv = parse_tree_elements(SAMPLE_TREE)
    assert "workout_row_0" in inv["cells"]
    assert "Push Day" in inv["statictexts"]


def test_parse_tree_elements_handles_empty_tree() -> None:
    inv = parse_tree_elements("")
    assert inv == {"tabs": [], "buttons": [], "cells": [], "statictexts": []}


def test_rewrite_swift_candidates_updates_tab_list(tmp_path: Path) -> None:
    swift = tmp_path / "AppUITests.swift"
    swift.write_text(
        """
import XCTest

final class AppUITests: XCTestCase {
    func test_history() throws {
        tapAnyTab(["history_tab", "History"])
        snapshot("iphone-history")
    }
}
""",
        encoding="utf-8",
    )
    inventories = {
        "iphone-history": {
            "tabs": ["History", "history_tab"],
            "buttons": [],
            "cells": [],
            "statictexts": [],
        }
    }
    changed = rewrite_swift_candidates(swift, inventories)
    # History was already in the list — the merged list is identical → no change
    assert changed == 0


def test_rewrite_swift_candidates_injects_new_labels(tmp_path: Path) -> None:
    swift = tmp_path / "AppUITests.swift"
    swift.write_text(
        """
import XCTest

final class AppUITests: XCTestCase {
    func test_editor() throws {
        tapFirstAvailable(["add_workout_button"])
        snapshot("iphone-workout-editor")
    }
}
""",
        encoding="utf-8",
    )
    inventories = {
        "iphone-workout-editor": {
            "tabs": [],
            "buttons": ["plus", "Add Workout"],
            "cells": [],
            "statictexts": [],
        }
    }
    changed = rewrite_swift_candidates(swift, inventories)
    assert changed == 1
    text = swift.read_text(encoding="utf-8")
    # New labels injected at the front, existing kept
    assert '"plus"' in text
    assert '"Add Workout"' in text
    assert '"add_workout_button"' in text


def test_rewrite_swift_candidates_skips_unknown_screens(tmp_path: Path) -> None:
    swift = tmp_path / "AppUITests.swift"
    original = """
import XCTest

final class AppUITests: XCTestCase {
    func test_unknown() throws {
        tapAnyTab(["Foo"])
        snapshot("never-captured-screen")
    }
}
"""
    swift.write_text(original, encoding="utf-8")
    changed = rewrite_swift_candidates(swift, {})
    assert changed == 0
    assert swift.read_text(encoding="utf-8") == original


def test_rewrite_swift_candidates_preserves_method_body(tmp_path: Path) -> None:
    swift = tmp_path / "AppUITests.swift"
    swift.write_text(
        """
import XCTest

final class AppUITests: XCTestCase {
    func test_complex() throws {
        if !app.launchArguments.contains("--mock") {
            app.terminate()
            app.launch()
        }
        tapFirstAvailable(["old_id"])
        settle(1.0)
        snapshot("paywall")
    }
}
""",
        encoding="utf-8",
    )
    inventories = {
        "paywall": {
            "tabs": [],
            "buttons": ["Subscribe", "Pro"],
            "cells": [],
            "statictexts": [],
        }
    }
    rewrite_swift_candidates(swift, inventories)
    text = swift.read_text(encoding="utf-8")
    # The mock-launch logic is preserved
    assert 'app.launchArguments.contains("--mock")' in text
    assert "settle(1.0)" in text
    # The candidate list got updated
    assert '"Subscribe"' in text
    assert '"old_id"' in text  # original kept as fallback
