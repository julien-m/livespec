"""Tests for validator/placeholders.py.

# @spec FR-011 / AC-010 — .specs/features/039-command-expectations-and-verify-output/spec.md#fr-011
"""

from __future__ import annotations

from validator.placeholders import resolve, run_date_from_timestamp


def test_resolve_feature():
    assert (
        resolve("<feature>/spec.md", feature="001-foo", run_date="2026-05-12")
        == "001-foo/spec.md"
    )


def test_resolve_date_from_artifact_timestamp_never_today():
    # AC-010 / EC-006: <date> comes from the artifact timestamp, never today.
    out = resolve("checks/<date>-test.md", feature=None, run_date="2026-05-12")
    assert out == "checks/2026-05-12-test.md"


def test_resolve_path_passthrough():
    # <path> is a documented passthrough (used inside larger templates).
    out = resolve("<path>/spec.md", feature=None, run_date="2026-05-12")
    assert out == "<path>/spec.md"


def test_resolve_combined():
    out = resolve(
        "<path>/<feature>/checks/<date>-test.md",
        feature="002-bar",
        run_date="2026-05-12",
    )
    assert out == "<path>/002-bar/checks/2026-05-12-test.md"


def test_resolve_feature_none_falls_through():
    out = resolve("<feature>/spec.md", feature=None, run_date="2026-05-12")
    assert out == "<feature>/spec.md"


def test_run_date_from_timestamp():
    assert run_date_from_timestamp("2026-05-12T10:00:00Z") == "2026-05-12"
    assert run_date_from_timestamp("2026-05-12") == "2026-05-12"
