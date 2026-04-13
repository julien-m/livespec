"""Reusable assertion helpers for LiveSpec integration tests."""

from pathlib import Path


def assert_specs_directory_valid(cwd: Path) -> None:
    """Check that .specs/ exists and contains the minimum required files."""
    specs = cwd / ".specs"
    assert specs.exists(), f".specs/ directory not found in {cwd}"
    assert specs.is_dir(), f".specs exists but is not a directory in {cwd}"

    required_files = [
        "project.md",
        "constitution.md",
        "roadmap.md",
        "README.md",
    ]
    for filename in required_files:
        path = specs / filename
        assert path.exists(), f"Required file missing: .specs/{filename}"
        content = path.read_text()
        assert len(content.strip()) > 0, f"Required file is empty: .specs/{filename}"


def assert_file_exists(path: Path, msg: str = "") -> None:
    """Assert that a file exists at the given path."""
    detail = f" ({msg})" if msg else ""
    assert path.exists(), f"File not found: {path}{detail}"
    assert path.is_file(), f"Path exists but is not a file: {path}{detail}"


def assert_roadmap_has_tiers(content: str) -> None:
    """Check that roadmap content contains all 4 HTML marker pairs."""
    tiers = ["mvp", "postmvp", "future", "deferred"]
    for tier in tiers:
        start = f"<!-- roadmap:{tier}:start -->"
        end = f"<!-- roadmap:{tier}:end -->"
        assert start in content, f"Missing roadmap marker: {start}"
        assert end in content, f"Missing roadmap marker: {end}"


def assert_adr_exists(specs_root: Path) -> None:
    """Check that at least one ADR file exists in the decisions directory."""
    decisions_dir = specs_root / "stacks" / "decisions"
    if not decisions_dir.exists():
        raise AssertionError(f"Decisions directory not found: {decisions_dir}")
    adrs = list(decisions_dir.glob("ADR-*.md"))
    assert len(adrs) >= 1, (
        f"No ADR files found in {decisions_dir}. At least one ADR is required by the quality gate."
    )
