# LiveSpec traceability anchors
# @spec(FR-005)

"""Unit tests for Go go.mod parsing."""

# @spec FR-005: Unit tests for go.mod parser
# — .specs/features/020-driver-go/spec.md#fr-005

from __future__ import annotations

import tempfile
from pathlib import Path

from validator.drivers.go_detector import (
    has_go_dependency,
    has_go_module,
    parse_go_dependencies,
    parse_go_module,
)

_GO_MOD_FULL = """module github.com/example/myapp

go 1.22

require (
\tgithub.com/leanovate/gopter v0.2.11
\tgithub.com/gkampitakis/go-snaps v0.5.4 // indirect
\tgithub.com/stretchr/testify v1.9.0
)

require github.com/google/uuid v1.6.0
"""


def _write_go_mod(project_root: Path, contents: str) -> None:
    """Write a ``go.mod`` file inside ``project_root``."""
    (project_root / "go.mod").write_text(contents, encoding="utf-8")


def test_parse_go_module_extracts_module_path() -> None:
    """The ``module`` line yields the declared module path."""
    # @spec FR-003 — .specs/features/020-driver-go/spec.md#fr-003
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        _write_go_mod(project_root, _GO_MOD_FULL)

        assert parse_go_module(str(project_root)) == "github.com/example/myapp"


def test_parse_go_module_supports_quoted_path() -> None:
    """``module "..."`` form is accepted (rare but legal)."""
    contents = 'module "example.com/quoted/path"\n'
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        _write_go_mod(project_root, contents)

        assert parse_go_module(str(project_root)) == "example.com/quoted/path"


def test_parse_go_module_missing_file_returns_none() -> None:
    """No go.mod -> None."""
    with tempfile.TemporaryDirectory() as tmpdir:
        assert parse_go_module(tmpdir) is None


def test_parse_go_module_no_module_line_returns_none() -> None:
    """A go.mod without a ``module`` directive yields None."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        _write_go_mod(project_root, "go 1.22\n")

        assert parse_go_module(str(project_root)) is None


def test_parse_go_dependencies_multi_line_block() -> None:
    """Multi-line ``require ( ... )`` blocks expose every entry."""
    # @spec FR-003, AC-005
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        _write_go_mod(project_root, _GO_MOD_FULL)

        deps = parse_go_dependencies(str(project_root))

    assert "github.com/leanovate/gopter" in deps
    assert "github.com/gkampitakis/go-snaps" in deps
    assert "github.com/stretchr/testify" in deps
    # Single-line require form is also picked up.
    assert "github.com/google/uuid" in deps


def test_parse_go_dependencies_strips_inline_indirect_comment() -> None:
    """``// indirect`` and other trailing comments are stripped from the path."""
    contents = """module example.com/x

require (
\tgithub.com/foo/bar v1.0.0 // indirect
)
"""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        _write_go_mod(project_root, contents)

        deps = parse_go_dependencies(str(project_root))

    assert deps == ["github.com/foo/bar"]


def test_parse_go_dependencies_handles_single_line_require() -> None:
    """The single-line ``require <path> <version>`` form is parsed."""
    contents = """module example.com/x

require github.com/single/dep v0.1.0
"""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        _write_go_mod(project_root, contents)

        assert parse_go_dependencies(str(project_root)) == ["github.com/single/dep"]


def test_parse_go_dependencies_missing_file_returns_empty() -> None:
    """No ``go.mod`` -> empty list."""
    with tempfile.TemporaryDirectory() as tmpdir:
        assert parse_go_dependencies(tmpdir) == []


def test_parse_go_dependencies_handles_unreadable() -> None:
    """A binary / unreadable go.mod degrades to an empty list."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        (project_root / "go.mod").write_bytes(b"\xff\xfe\x00\x00")

        assert parse_go_dependencies(str(project_root)) == []


def test_parse_go_dependencies_dedupes() -> None:
    """Repeated entries collapse to a single result."""
    contents = """module example.com/x

require (
\tgithub.com/dup/lib v1.0.0
\tgithub.com/dup/lib v1.0.0
)
"""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        _write_go_mod(project_root, contents)

        assert parse_go_dependencies(str(project_root)) == ["github.com/dup/lib"]


def test_has_go_dependency_substring_match() -> None:
    """``has_go_dependency`` matches by substring against module paths."""
    # @spec AC-004, AC-005
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        _write_go_mod(project_root, _GO_MOD_FULL)

        # Trailing-name match (case-insensitive).
        assert has_go_dependency(str(project_root), "gopter") is True
        assert has_go_dependency(str(project_root), "GoPter") is True
        assert has_go_dependency(str(project_root), "go-snaps") is True
        # Full-path match.
        assert has_go_dependency(str(project_root), "github.com/leanovate/gopter") is True
        # Negative case.
        assert has_go_dependency(str(project_root), "cupaloy") is False


def test_has_go_dependency_empty_name_returns_false() -> None:
    """An empty needle never matches."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        _write_go_mod(project_root, _GO_MOD_FULL)

        assert has_go_dependency(str(project_root), "") is False
        assert has_go_dependency(str(project_root), "   ") is False


def test_has_go_module_true_when_present() -> None:
    """``has_go_module`` returns True when ``go.mod`` exists."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        _write_go_mod(project_root, _GO_MOD_FULL)

        assert has_go_module(str(project_root)) is True


def test_has_go_module_false_when_absent() -> None:
    """No ``go.mod`` -> False."""
    with tempfile.TemporaryDirectory() as tmpdir:
        assert has_go_module(tmpdir) is False
