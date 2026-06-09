# LiveSpec traceability anchors
# @spec(FR-005)

"""Unit tests for Cargo.toml dependency parsing and cargo-mutants JSON parser."""

# @spec FR-005: Unit tests for Cargo.toml parser and cargo-mutants JSON parser
# — .specs/features/021-driver-rust/spec.md#fr-005

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from validator.drivers.rust_detector import (
    has_cargo_dependency,
    has_cargo_manifest,
    parse_cargo_dependencies,
    parse_cargo_mutants_json,
)

_CARGO_TOML_FULL = """[package]
name = "myapp"
version = "0.1.0"
edition = "2021"

[dependencies]
serde = "1.0"
tokio = { version = "1", features = ["full"] }

[dev-dependencies]
insta = "1.34"
proptest = { version = "1.4", default-features = false }
quickcheck = "1.0"

[build-dependencies]
cc = "1.0"
"""


def _write_cargo_toml(project_root: Path, contents: str) -> None:
    """Write a ``Cargo.toml`` file inside ``project_root``."""
    (project_root / "Cargo.toml").write_text(contents, encoding="utf-8")


# ---------------------------------------------------------------------------
# parse_cargo_dependencies
# ---------------------------------------------------------------------------


def test_parse_cargo_dependencies_extracts_all_tables() -> None:
    """``[dependencies]``, ``[dev-dependencies]`` and ``[build-dependencies]`` are all walked."""
    # @spec FR-002, AC-010
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        _write_cargo_toml(project_root, _CARGO_TOML_FULL)

        deps = parse_cargo_dependencies(str(project_root))

    # Names from every table must be present.
    assert "serde" in deps
    assert "tokio" in deps
    assert "insta" in deps
    assert "proptest" in deps
    assert "quickcheck" in deps
    assert "cc" in deps


def test_parse_cargo_dependencies_handles_string_value_form() -> None:
    """``dep = "1.0"`` syntax is supported."""
    # @spec SC-004
    contents = """[package]
name = "x"
version = "0.1.0"

[dependencies]
serde = "1.0"
"""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        _write_cargo_toml(project_root, contents)

        assert parse_cargo_dependencies(str(project_root)) == ["serde"]


def test_parse_cargo_dependencies_handles_table_value_form() -> None:
    """``dep = { version = "1.0", features = [...] }`` syntax is supported."""
    # @spec SC-004
    contents = """[package]
name = "x"
version = "0.1.0"

[dependencies]
tokio = { version = "1", features = ["full"] }
"""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        _write_cargo_toml(project_root, contents)

        assert parse_cargo_dependencies(str(project_root)) == ["tokio"]


def test_parse_cargo_dependencies_missing_file_returns_empty() -> None:
    """No ``Cargo.toml`` -> empty list, no raise."""
    with tempfile.TemporaryDirectory() as tmpdir:
        assert parse_cargo_dependencies(tmpdir) == []


def test_parse_cargo_dependencies_malformed_toml_returns_empty() -> None:
    """A malformed ``Cargo.toml`` yields ``[]`` (no exception)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        _write_cargo_toml(project_root, "this is = not valid = toml = at all\n[")

        assert parse_cargo_dependencies(str(project_root)) == []


def test_parse_cargo_dependencies_unreadable_returns_empty() -> None:
    """A binary / unreadable Cargo.toml degrades to an empty list."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        (project_root / "Cargo.toml").write_bytes(b"\xff\xfe\x00\x00")

        assert parse_cargo_dependencies(str(project_root)) == []


def test_parse_cargo_dependencies_dedupes_and_lowercases() -> None:
    """Duplicate names across tables collapse to one lowercase entry."""
    contents = """[package]
name = "x"
version = "0.1.0"

[dependencies]
Serde = "1.0"

[dev-dependencies]
serde = "1.0"
"""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        _write_cargo_toml(project_root, contents)

        assert parse_cargo_dependencies(str(project_root)) == ["serde"]


# ---------------------------------------------------------------------------
# has_cargo_dependency
# ---------------------------------------------------------------------------


def test_has_cargo_dependency_case_insensitive() -> None:
    """``has_cargo_dependency`` matches case-insensitively against crate names."""
    # @spec AC-004, AC-006
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        _write_cargo_toml(project_root, _CARGO_TOML_FULL)

        assert has_cargo_dependency(str(project_root), "insta") is True
        assert has_cargo_dependency(str(project_root), "InSta") is True
        assert has_cargo_dependency(str(project_root), "PROPTEST") is True
        assert has_cargo_dependency(str(project_root), "quickcheck") is True
        assert has_cargo_dependency(str(project_root), "missing-crate") is False


def test_has_cargo_dependency_empty_name_returns_false() -> None:
    """An empty / whitespace needle never matches."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        _write_cargo_toml(project_root, _CARGO_TOML_FULL)

        assert has_cargo_dependency(str(project_root), "") is False
        assert has_cargo_dependency(str(project_root), "   ") is False


# ---------------------------------------------------------------------------
# has_cargo_manifest
# ---------------------------------------------------------------------------


def test_has_cargo_manifest_true_when_present() -> None:
    """``has_cargo_manifest`` returns True when ``Cargo.toml`` exists."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        _write_cargo_toml(project_root, _CARGO_TOML_FULL)

        assert has_cargo_manifest(str(project_root)) is True


def test_has_cargo_manifest_false_when_absent() -> None:
    """No ``Cargo.toml`` -> False."""
    with tempfile.TemporaryDirectory() as tmpdir:
        assert has_cargo_manifest(tmpdir) is False


# ---------------------------------------------------------------------------
# parse_cargo_mutants_json
# ---------------------------------------------------------------------------


def test_parse_cargo_mutants_json_extracts_summary_object() -> None:
    """A single-object summary yields the expected counts."""
    # @spec FR-003, AC-008
    payload = json.dumps({"caught": 12, "missed": 3, "timeout": 1, "unviable": 0})

    counts = parse_cargo_mutants_json(payload)

    assert counts == {"caught": 12, "missed": 3, "timeout": 1, "unviable": 0}


def test_parse_cargo_mutants_json_supports_nested_outcomes() -> None:
    """Nested ``outcomes`` / ``summary`` shapes are also recognised."""
    payload = json.dumps(
        {
            "version": "24.4.0",
            "outcomes": {"caught": 5, "missed": 2, "timeout": 0, "unviable": 1},
        }
    )

    counts = parse_cargo_mutants_json(payload)

    assert counts == {"caught": 5, "missed": 2, "timeout": 0, "unviable": 1}


def test_parse_cargo_mutants_json_aggregates_per_mutant_lines() -> None:
    """Line-delimited per-mutant events are aggregated by ``outcome``."""
    payload = "\n".join(
        [
            json.dumps({"mutant": "m1", "outcome": "caught"}),
            json.dumps({"mutant": "m2", "outcome": "caught"}),
            json.dumps({"mutant": "m3", "outcome": "missed"}),
            json.dumps({"mutant": "m4", "outcome": "timeout"}),
            json.dumps({"mutant": "m5", "outcome": "unviable"}),
        ]
    )

    counts = parse_cargo_mutants_json(payload)

    assert counts == {"caught": 2, "missed": 1, "timeout": 1, "unviable": 1}


def test_parse_cargo_mutants_json_zero_fills_missing_keys() -> None:
    """Absent outcome keys default to zero."""
    payload = json.dumps({"caught": 10})

    counts = parse_cargo_mutants_json(payload)

    assert counts == {"caught": 10, "missed": 0, "timeout": 0, "unviable": 0}


def test_parse_cargo_mutants_json_malformed_returns_zeros() -> None:
    """Garbage input yields all-zero counts (no raise)."""
    counts = parse_cargo_mutants_json("not json at all { [ ")

    assert counts == {"caught": 0, "missed": 0, "timeout": 0, "unviable": 0}


def test_parse_cargo_mutants_json_empty_returns_zeros() -> None:
    """Empty stdout yields all-zero counts."""
    counts = parse_cargo_mutants_json("")

    assert counts == {"caught": 0, "missed": 0, "timeout": 0, "unviable": 0}


def test_parse_cargo_mutants_json_ignores_unknown_outcome_strings() -> None:
    """Unknown outcome labels are silently ignored."""
    payload = "\n".join(
        [
            json.dumps({"outcome": "caught"}),
            json.dumps({"outcome": "totally-unknown"}),
            json.dumps({"outcome": "missed"}),
        ]
    )

    counts = parse_cargo_mutants_json(payload)

    assert counts == {"caught": 1, "missed": 1, "timeout": 0, "unviable": 0}
