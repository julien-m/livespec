"""Tests for coherence graph builder — disk-based parsing of .specs/ structure."""

from __future__ import annotations

from pathlib import Path

import pytest

from validator.coherence.graph_builder import build_graph


@pytest.fixture
def specs_dir(tmp_path: Path) -> Path:
    """Create a fully populated .specs/ structure for graph building."""
    root = tmp_path / ".specs"
    root.mkdir()

    # roadmap.md with checked/unchecked items, with/without links
    (root / "roadmap.md").write_text(
        "# Roadmap\n\n"
        "- [x] [Auth](features/001-auth/)\n"
        "- [ ] [Search](features/002-search/)\n"
        "- [x] Done item without link\n"
        "- [ ] Future item\n"
    )

    # features/001-auth with spec.md (frontmatter), plan.md, implementation.md
    auth_dir = root / "features" / "001-auth"
    auth_dir.mkdir(parents=True)
    (auth_dir / "spec.md").write_text(
        "---\nstatus: Implemented\n---\n# Auth Feature\n"
    )
    (auth_dir / "plan.md").write_text("# Plan\n")
    (auth_dir / "implementation.md").write_text(
        "# Implementation\n\n"
        "| FR-001 | Login | src/auth/login.ts |\n"
        "| AC-001 | Redirect | src/auth/redirect.ts |\n"
        "\n@spec(FR-001) mapped\n"
    )

    # features/002-search with spec.md only
    search_dir = root / "features" / "002-search"
    search_dir.mkdir(parents=True)
    (search_dir / "spec.md").write_text(
        "---\nstatus: Draft\n---\n# Search Feature\n"
    )

    # README.md referencing features
    (root / "README.md").write_text(
        "# Project\n\n"
        "| [001-auth](features/001-auth/) | Implemented |\n"
        "| [002-search](features/002-search/) | Draft |\n"
    )

    # stacks/_default.md
    stacks_dir = root / "stacks"
    stacks_dir.mkdir()
    (stacks_dir / "_default.md").write_text(
        "# Stack\n\n## Stack\n\n- TypeScript\n- React\n- PostgreSQL\n"
    )

    # preflight.md
    (root / "preflight.md").write_text(
        "# Preflight\n\n- TypeScript compiler installed\n- PostgreSQL running\n"
    )

    # changelog.md
    (root / "changelog.md").write_text(
        "# Changelog\n\n- Added 001-auth login flow\n- Started 002-search indexing\n"
    )

    return root


class TestBuildGraph:
    """Test build_graph with a realistic .specs/ structure."""

    def test_roadmap_items_parsed(self, specs_dir: Path) -> None:
        graph = build_graph(specs_dir)
        assert len(graph.roadmap) == 4

        checked_items = [i for i in graph.roadmap if i.checked]
        unchecked_items = [i for i in graph.roadmap if not i.checked]
        assert len(checked_items) == 2
        assert len(unchecked_items) == 2

    def test_roadmap_item_with_link(self, specs_dir: Path) -> None:
        graph = build_graph(specs_dir)
        auth_item = graph.roadmap[0]
        assert auth_item.name == "Auth"
        assert auth_item.link == "features/001-auth/"
        assert auth_item.checked is True

    def test_roadmap_item_without_link(self, specs_dir: Path) -> None:
        graph = build_graph(specs_dir)
        done_item = graph.roadmap[2]
        assert done_item.name == "Done item without link"
        assert done_item.link is None
        assert done_item.checked is True

    def test_features_detected(self, specs_dir: Path) -> None:
        graph = build_graph(specs_dir)
        assert len(graph.features) == 2
        dirs = {f.dir_name for f in graph.features}
        assert dirs == {"001-auth", "002-search"}

    def test_feature_files_map(self, specs_dir: Path) -> None:
        graph = build_graph(specs_dir)
        auth = graph.get_feature("001-auth")
        assert auth is not None
        assert auth.files["spec"] is True
        assert auth.files["plan"] is True
        assert auth.files["implementation"] is True
        assert auth.files["progress"] is False

    def test_feature_status_from_frontmatter(self, specs_dir: Path) -> None:
        graph = build_graph(specs_dir)
        auth = graph.get_feature("001-auth")
        assert auth is not None
        assert auth.status == "Implemented"

        search = graph.get_feature("002-search")
        assert search is not None
        assert search.status == "Draft"

    def test_implementation_paths_parsed(self, specs_dir: Path) -> None:
        graph = build_graph(specs_dir)
        auth = graph.get_feature("001-auth")
        assert auth is not None
        assert "FR-001" in auth.implementation_paths
        assert "src/auth/login.ts" in auth.implementation_paths["FR-001"]
        assert "AC-001" in auth.implementation_paths
        assert "src/auth/redirect.ts" in auth.implementation_paths["AC-001"]

    def test_spec_anchors_parsed(self, specs_dir: Path) -> None:
        graph = build_graph(specs_dir)
        auth = graph.get_feature("001-auth")
        assert auth is not None
        assert "FR-001" in auth.spec_anchors

    def test_readme_entries(self, specs_dir: Path) -> None:
        graph = build_graph(specs_dir)
        assert "001-auth" in graph.readme_entries
        assert "002-search" in graph.readme_entries

    def test_readme_statuses(self, specs_dir: Path) -> None:
        graph = build_graph(specs_dir)
        assert graph.readme_statuses.get("001-auth") == "Implemented"
        assert graph.readme_statuses.get("002-search") == "Draft"

    def test_stack_technologies(self, specs_dir: Path) -> None:
        graph = build_graph(specs_dir)
        assert "TypeScript" in graph.stack_technologies
        assert "React" in graph.stack_technologies
        assert "PostgreSQL" in graph.stack_technologies

    def test_preflight_checks(self, specs_dir: Path) -> None:
        graph = build_graph(specs_dir)
        assert len(graph.preflight_checks) >= 2
        assert any("TypeScript" in c for c in graph.preflight_checks)

    def test_changelog_refs(self, specs_dir: Path) -> None:
        graph = build_graph(specs_dir)
        assert "001-auth" in graph.changelog_refs
        assert "002-search" in graph.changelog_refs

    def test_feature_dirs_property(self, specs_dir: Path) -> None:
        graph = build_graph(specs_dir)
        assert graph.feature_dirs == {"001-auth", "002-search"}

    def test_get_feature_returns_none_for_unknown(self, specs_dir: Path) -> None:
        graph = build_graph(specs_dir)
        assert graph.get_feature("999-nonexistent") is None


class TestBuildGraphMissingFiles:
    """Test graceful handling of missing files."""

    def test_empty_specs_dir(self, tmp_path: Path) -> None:
        root = tmp_path / ".specs"
        root.mkdir()
        graph = build_graph(root)
        assert graph.roadmap == []
        assert graph.features == []
        assert graph.readme_entries == []
        assert graph.stack_technologies == []
        assert graph.preflight_checks == []
        assert graph.changelog_refs == []

    def test_no_roadmap(self, tmp_path: Path) -> None:
        root = tmp_path / ".specs"
        root.mkdir()
        (root / "features").mkdir()
        graph = build_graph(root)
        assert graph.roadmap == []

    def test_no_features_dir(self, tmp_path: Path) -> None:
        root = tmp_path / ".specs"
        root.mkdir()
        (root / "roadmap.md").write_text("- [ ] Something\n")
        graph = build_graph(root)
        assert graph.features == []

    def test_no_readme(self, tmp_path: Path) -> None:
        root = tmp_path / ".specs"
        root.mkdir()
        graph = build_graph(root)
        assert graph.readme_entries == []
        assert graph.readme_statuses == {}

    def test_no_stack(self, tmp_path: Path) -> None:
        root = tmp_path / ".specs"
        root.mkdir()
        graph = build_graph(root)
        assert graph.stack_technologies == []

    def test_no_changelog(self, tmp_path: Path) -> None:
        root = tmp_path / ".specs"
        root.mkdir()
        graph = build_graph(root)
        assert graph.changelog_refs == []

    def test_feature_without_spec_md(self, tmp_path: Path) -> None:
        root = tmp_path / ".specs"
        root.mkdir()
        feat_dir = root / "features" / "001-bare"
        feat_dir.mkdir(parents=True)
        graph = build_graph(root)
        assert len(graph.features) == 1
        feat = graph.features[0]
        assert feat.status is None
        assert feat.spec_mtime is None
        assert feat.files["spec"] is False
