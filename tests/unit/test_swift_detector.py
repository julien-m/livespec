# LiveSpec traceability anchors
# @spec(FR-006)

"""Unit tests for Swift Package.swift parsing and Xcode-only detection."""

# @spec FR-006: Unit tests for Swift detector
# — .specs/features/019-driver-swift/spec.md#fr-006

from __future__ import annotations

import tempfile
from pathlib import Path

from validator.drivers.swift_detector import (
    has_swift_dependency,
    has_swift_package,
    is_xcode_only_project,
    parse_package_dependencies,
)

_PACKAGE_SWIFT_FULL = """// swift-tools-version:5.9
import PackageDescription

let package = Package(
    name: "MyApp",
    dependencies: [
        .package(url: "https://github.com/pointfreeco/swift-snapshot-testing.git", from: "1.15.0"),
        .package(url: "https://github.com/typelift/SwiftCheck", from: "0.12.0"),
        .package(name: "Alamofire", url: "https://github.com/Alamofire/Alamofire.git"),
    ],
    targets: [
        .target(name: "MyApp"),
        .testTarget(name: "MyAppTests", dependencies: ["MyApp"]),
    ]
)
"""


def _write_package_swift(project_root: Path, contents: str) -> None:
    """Write a Package.swift file inside ``project_root``."""
    (project_root / "Package.swift").write_text(contents, encoding="utf-8")


def test_parse_package_dependencies_extracts_url_names() -> None:
    """Dependencies declared via ``.package(url:)`` are returned by trailing name."""
    # @spec FR-003 — .specs/features/019-driver-swift/spec.md#fr-003
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        _write_package_swift(project_root, _PACKAGE_SWIFT_FULL)

        deps = parse_package_dependencies(str(project_root))

    assert "swift-snapshot-testing" in deps
    assert "swiftcheck" in deps
    assert "alamofire" in deps


def test_parse_package_dependencies_missing_file_returns_empty() -> None:
    """No Package.swift means no declared dependencies."""
    with tempfile.TemporaryDirectory() as tmpdir:
        assert parse_package_dependencies(tmpdir) == []


def test_parse_package_dependencies_handles_unreadable() -> None:
    """A binary / unreadable Package.swift degrades to an empty list."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        # Write bytes that are not valid UTF-8.
        (project_root / "Package.swift").write_bytes(b"\xff\xfe\x00\x00")

        assert parse_package_dependencies(str(project_root)) == []


def test_parse_package_dependencies_dedupes() -> None:
    """Duplicate URLs with and without ``.git`` collapse to a single entry."""
    contents = """\
let package = Package(
    name: "X",
    dependencies: [
        .package(url: "https://example.com/Foo.git", from: "1.0.0"),
        .package(url: "https://example.com/Foo", from: "1.0.0"),
    ]
)
"""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        _write_package_swift(project_root, contents)

        deps = parse_package_dependencies(str(project_root))

    assert deps == ["foo"]


def test_has_swift_dependency_case_insensitive() -> None:
    """``has_swift_dependency`` ignores case and matches by name."""
    # @spec AC-005, AC-006
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        _write_package_swift(project_root, _PACKAGE_SWIFT_FULL)

        assert has_swift_dependency(str(project_root), "swift-snapshot-testing") is True
        assert has_swift_dependency(str(project_root), "Swift-Snapshot-Testing") is True
        assert has_swift_dependency(str(project_root), "SwiftCheck") is True
        assert has_swift_dependency(str(project_root), "Quick") is False


def test_has_swift_dependency_empty_name_returns_false() -> None:
    """An empty needle never matches."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        _write_package_swift(project_root, _PACKAGE_SWIFT_FULL)

        assert has_swift_dependency(str(project_root), "") is False
        assert has_swift_dependency(str(project_root), "   ") is False


def test_has_swift_package_true_when_present() -> None:
    """``has_swift_package`` returns ``True`` when Package.swift exists."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        _write_package_swift(project_root, _PACKAGE_SWIFT_FULL)

        assert has_swift_package(str(project_root)) is True


def test_has_swift_package_false_when_absent() -> None:
    """No Package.swift -> False."""
    with tempfile.TemporaryDirectory() as tmpdir:
        assert has_swift_package(tmpdir) is False


def test_is_xcode_only_project_true_with_xcodeproj() -> None:
    """A project with .xcodeproj and no Package.swift is Xcode-only."""
    # @spec AC-004 — .specs/features/019-driver-swift/spec.md#ac-004
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        (project_root / "MyApp.xcodeproj").mkdir()

        assert is_xcode_only_project(str(project_root)) is True


def test_is_xcode_only_project_false_when_package_swift_present() -> None:
    """When both Package.swift and .xcodeproj exist, prefer SwiftPM."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        _write_package_swift(project_root, _PACKAGE_SWIFT_FULL)
        (project_root / "MyApp.xcodeproj").mkdir()

        assert is_xcode_only_project(str(project_root)) is False


def test_is_xcode_only_project_false_for_empty_dir() -> None:
    """An empty directory is not Xcode-only either."""
    with tempfile.TemporaryDirectory() as tmpdir:
        assert is_xcode_only_project(tmpdir) is False
