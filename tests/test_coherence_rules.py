"""Tests for each individual coherence rule — pure dataclass construction, no disk I/O."""

from __future__ import annotations

from pathlib import Path

import pytest

from validator.coherence.graph_builder import FeatureInfo, RoadmapItem, SpecGraph
from validator.coherence.rules.r1_roadmap_features import (
    R1_1_RoadmapFeatureMissing,
    R1_2_OrphanFeature,
    R1_3_StatusRoadmapMismatch,
    R1_4_CheckedNoLink,
)
from validator.coherence.rules.r2_status_files import (
    R2_1_RequiredFileAbsent,
    R2_2_AdvancedFileForLowStatus,
    R2_3_InvalidStatus,
)
from validator.coherence.rules.r3_spec_anchors import (
    R3_1_SourceFileNotFound,
    R3_2_SpecAnchorMissing,
)
from validator.coherence.rules.r4_readme_sync import (
    R4_1_ReadmeFeatureMissing,
    R4_2_DiskFeatureMissingReadme,
    R4_3_ReadmeStatusMismatch,
)
from validator.coherence.rules.r5_stack_preflight import R5_1_StackNoPreflight
from validator.coherence.rules.r6_changelog_refs import R6_1_ChangelogFeatureMissing
from validator.coherence.violation import Severity


def _make_feature(
    dir_name: str = "001-auth",
    num: int = 1,
    slug: str = "auth",
    status: str | None = "Draft",
    files: dict[str, bool] | None = None,
    spec_anchors: list[str] | None = None,
    implementation_paths: dict[str, list[str]] | None = None,
    spec_mtime: float | None = None,
) -> FeatureInfo:
    return FeatureInfo(
        dir_name=dir_name,
        num=num,
        slug=slug,
        status=status,
        files=files or {"spec": True, "plan": True, "implementation": False, "progress": False, "changelog": False},
        spec_anchors=spec_anchors or [],
        implementation_paths=implementation_paths or {},
        spec_mtime=spec_mtime,
    )


def _make_roadmap_item(
    name: str = "Auth",
    slug: str = "001-auth",
    checked: bool = False,
    link: str | None = "features/001-auth/",
    line_number: int = 1,
) -> RoadmapItem:
    return RoadmapItem(name=name, slug=slug, checked=checked, link=link, line_number=line_number)


# ---------------------------------------------------------------------------
# R1 — Roadmap / Features
# ---------------------------------------------------------------------------


class TestR1_1_RoadmapFeatureMissing:
    def test_checked_link_to_missing_feature(self) -> None:
        graph = SpecGraph(
            roadmap=[_make_roadmap_item(checked=True, link="features/001-auth/")],
            features=[],
        )
        violations = R1_1_RoadmapFeatureMissing().check(graph)
        assert len(violations) == 1
        assert violations[0].severity == Severity.ERROR
        assert "001-auth" in violations[0].message

    def test_checked_link_to_existing_feature(self) -> None:
        graph = SpecGraph(
            roadmap=[_make_roadmap_item(checked=True, link="features/001-auth/")],
            features=[_make_feature()],
        )
        violations = R1_1_RoadmapFeatureMissing().check(graph)
        assert violations == []

    def test_unchecked_item_ignored(self) -> None:
        graph = SpecGraph(
            roadmap=[_make_roadmap_item(checked=False, link="features/001-auth/")],
            features=[],
        )
        violations = R1_1_RoadmapFeatureMissing().check(graph)
        assert violations == []

    def test_no_link_ignored(self) -> None:
        graph = SpecGraph(
            roadmap=[_make_roadmap_item(checked=True, link=None)],
            features=[],
        )
        violations = R1_1_RoadmapFeatureMissing().check(graph)
        assert violations == []


class TestR1_2_OrphanFeature:
    def test_feature_not_in_roadmap(self) -> None:
        graph = SpecGraph(
            roadmap=[],
            features=[_make_feature(dir_name="001-auth", slug="auth")],
        )
        violations = R1_2_OrphanFeature().check(graph)
        assert len(violations) == 1
        assert violations[0].severity == Severity.WARNING

    def test_feature_in_roadmap_via_link(self) -> None:
        graph = SpecGraph(
            roadmap=[_make_roadmap_item(link="features/001-auth/")],
            features=[_make_feature()],
        )
        violations = R1_2_OrphanFeature().check(graph)
        assert violations == []

    def test_feature_in_roadmap_via_slug(self) -> None:
        # roadmap_refs collects item.slug, so "001-auth" matches feature dir_name "001-auth"
        graph = SpecGraph(
            roadmap=[_make_roadmap_item(slug="001-auth", link=None)],
            features=[_make_feature(dir_name="001-auth", slug="auth")],
        )
        violations = R1_2_OrphanFeature().check(graph)
        assert violations == []

    def test_feature_truly_orphan(self) -> None:
        graph = SpecGraph(
            roadmap=[_make_roadmap_item(slug="other", link=None, name="Other")],
            features=[_make_feature(dir_name="001-auth", slug="auth")],
        )
        violations = R1_2_OrphanFeature().check(graph)
        assert len(violations) == 1


class TestR1_3_StatusRoadmapMismatch:
    def test_implemented_but_unchecked(self) -> None:
        graph = SpecGraph(
            roadmap=[_make_roadmap_item(checked=False, link="features/001-auth/")],
            features=[_make_feature(status="Implemented")],
        )
        violations = R1_3_StatusRoadmapMismatch().check(graph)
        assert len(violations) == 1
        assert violations[0].severity == Severity.ERROR
        assert "Implemented" in violations[0].message

    def test_draft_but_checked(self) -> None:
        graph = SpecGraph(
            roadmap=[_make_roadmap_item(checked=True, link="features/001-auth/")],
            features=[_make_feature(status="Draft")],
        )
        violations = R1_3_StatusRoadmapMismatch().check(graph)
        assert len(violations) == 1
        assert violations[0].severity == Severity.ERROR

    def test_implemented_and_checked_is_valid(self) -> None:
        graph = SpecGraph(
            roadmap=[_make_roadmap_item(checked=True, link="features/001-auth/")],
            features=[_make_feature(status="Implemented")],
        )
        violations = R1_3_StatusRoadmapMismatch().check(graph)
        assert violations == []

    def test_deprecated_status_skipped(self) -> None:
        graph = SpecGraph(
            roadmap=[_make_roadmap_item(checked=False, link="features/001-auth/")],
            features=[_make_feature(status="Deprecated")],
        )
        violations = R1_3_StatusRoadmapMismatch().check(graph)
        assert violations == []


class TestR1_4_CheckedNoLink:
    def test_checked_no_link(self) -> None:
        graph = SpecGraph(
            roadmap=[_make_roadmap_item(checked=True, link=None)],
        )
        violations = R1_4_CheckedNoLink().check(graph)
        assert len(violations) == 1
        assert violations[0].severity == Severity.WARNING

    def test_checked_with_non_feature_link(self) -> None:
        graph = SpecGraph(
            roadmap=[_make_roadmap_item(checked=True, link="https://example.com")],
        )
        violations = R1_4_CheckedNoLink().check(graph)
        assert len(violations) == 1
        assert violations[0].severity == Severity.WARNING

    def test_checked_with_feature_link_is_valid(self) -> None:
        graph = SpecGraph(
            roadmap=[_make_roadmap_item(checked=True, link="features/001-auth/")],
        )
        violations = R1_4_CheckedNoLink().check(graph)
        assert violations == []

    def test_unchecked_ignored(self) -> None:
        graph = SpecGraph(
            roadmap=[_make_roadmap_item(checked=False, link=None)],
        )
        violations = R1_4_CheckedNoLink().check(graph)
        assert violations == []


# ---------------------------------------------------------------------------
# R2 — Status / Files
# ---------------------------------------------------------------------------


class TestR2_1_RequiredFileAbsent:
    def test_planned_missing_plan(self) -> None:
        graph = SpecGraph(
            features=[_make_feature(
                status="Planned",
                files={"spec": True, "plan": False, "implementation": False, "progress": False, "changelog": False},
            )],
        )
        violations = R2_1_RequiredFileAbsent().check(graph)
        assert len(violations) == 1
        assert violations[0].severity == Severity.ERROR
        assert "plan.md" in violations[0].message

    def test_planned_with_all_files_is_valid(self) -> None:
        graph = SpecGraph(
            features=[_make_feature(
                status="Planned",
                files={"spec": True, "plan": True, "implementation": False, "progress": False, "changelog": False},
            )],
        )
        violations = R2_1_RequiredFileAbsent().check(graph)
        assert violations == []

    def test_no_status_skipped(self) -> None:
        graph = SpecGraph(features=[_make_feature(status=None)])
        violations = R2_1_RequiredFileAbsent().check(graph)
        assert violations == []


class TestR2_2_AdvancedFileForLowStatus:
    def test_draft_with_implementation(self) -> None:
        graph = SpecGraph(
            features=[_make_feature(
                status="Draft",
                files={"spec": True, "plan": False, "implementation": True, "progress": False, "changelog": False},
            )],
        )
        violations = R2_2_AdvancedFileForLowStatus().check(graph)
        assert len(violations) == 1
        assert violations[0].severity == Severity.WARNING

    def test_draft_without_implementation_is_valid(self) -> None:
        graph = SpecGraph(
            features=[_make_feature(
                status="Draft",
                files={"spec": True, "plan": False, "implementation": False, "progress": False, "changelog": False},
            )],
        )
        violations = R2_2_AdvancedFileForLowStatus().check(graph)
        assert violations == []

    def test_implemented_with_implementation_is_valid(self) -> None:
        graph = SpecGraph(
            features=[_make_feature(
                status="Implemented",
                files={"spec": True, "plan": True, "implementation": True, "progress": False, "changelog": False},
            )],
        )
        violations = R2_2_AdvancedFileForLowStatus().check(graph)
        assert violations == []


class TestR2_3_InvalidStatus:
    def test_unknown_status(self) -> None:
        graph = SpecGraph(features=[_make_feature(status="Unknown")])
        violations = R2_3_InvalidStatus().check(graph)
        assert len(violations) == 1
        assert violations[0].severity == Severity.ERROR
        assert "Unknown" in violations[0].message

    def test_valid_statuses_pass(self) -> None:
        for status in ("Draft", "Planned", "In Progress", "Approved", "Implemented", "Deprecated", "Review"):
            graph = SpecGraph(features=[_make_feature(status=status)])
            violations = R2_3_InvalidStatus().check(graph)
            assert violations == [], f"Status '{status}' should be valid"

    def test_none_status_skipped(self) -> None:
        graph = SpecGraph(features=[_make_feature(status=None)])
        violations = R2_3_InvalidStatus().check(graph)
        assert violations == []


# ---------------------------------------------------------------------------
# R3 — Spec Anchors (needs specs_root for filesystem access)
# ---------------------------------------------------------------------------


class TestR3_1_SourceFileNotFound:
    def test_missing_source_file(self, tmp_path: Path) -> None:
        specs_root = tmp_path / ".specs"
        specs_root.mkdir()
        graph = SpecGraph(
            features=[_make_feature(
                implementation_paths={"FR-001": ["src/auth/login.ts"]},
            )],
        )
        rule = R3_1_SourceFileNotFound()
        rule.specs_root = specs_root
        violations = rule.check(graph)
        assert len(violations) == 1
        assert violations[0].severity == Severity.WARNING
        assert "src/auth/login.ts" in violations[0].message

    def test_existing_source_file(self, tmp_path: Path) -> None:
        specs_root = tmp_path / ".specs"
        specs_root.mkdir()
        src_file = tmp_path / "src" / "auth" / "login.ts"
        src_file.parent.mkdir(parents=True)
        src_file.write_text("// login")
        graph = SpecGraph(
            features=[_make_feature(
                implementation_paths={"FR-001": ["src/auth/login.ts"]},
            )],
        )
        rule = R3_1_SourceFileNotFound()
        rule.specs_root = specs_root
        violations = rule.check(graph)
        assert violations == []

    def test_no_specs_root_returns_empty(self) -> None:
        graph = SpecGraph(
            features=[_make_feature(
                implementation_paths={"FR-001": ["src/auth/login.ts"]},
            )],
        )
        rule = R3_1_SourceFileNotFound()
        violations = rule.check(graph)
        assert violations == []

    def test_no_implementation_paths_is_valid(self, tmp_path: Path) -> None:
        specs_root = tmp_path / ".specs"
        specs_root.mkdir()
        graph = SpecGraph(features=[_make_feature()])
        rule = R3_1_SourceFileNotFound()
        rule.specs_root = specs_root
        violations = rule.check(graph)
        assert violations == []


class TestR3_2_SpecAnchorMissing:
    def test_anchor_not_in_source(self, tmp_path: Path) -> None:
        specs_root = tmp_path / ".specs"
        specs_root.mkdir()
        src_file = tmp_path / "src" / "auth.ts"
        src_file.parent.mkdir(parents=True)
        src_file.write_text("// no anchor here\nfunction login() {}\n")
        graph = SpecGraph(
            features=[_make_feature(
                implementation_paths={"FR-001": ["src/auth.ts"]},
            )],
        )
        rule = R3_2_SpecAnchorMissing()
        rule.specs_root = specs_root
        violations = rule.check(graph)
        assert len(violations) == 1
        assert violations[0].severity == Severity.INFO
        assert "@spec(FR-001)" in violations[0].message

    def test_anchor_present_in_source(self, tmp_path: Path) -> None:
        specs_root = tmp_path / ".specs"
        specs_root.mkdir()
        src_file = tmp_path / "src" / "auth.ts"
        src_file.parent.mkdir(parents=True)
        src_file.write_text("// @spec(FR-001)\nfunction login() {}\n")
        graph = SpecGraph(
            features=[_make_feature(
                implementation_paths={"FR-001": ["src/auth.ts"]},
            )],
        )
        rule = R3_2_SpecAnchorMissing()
        rule.specs_root = specs_root
        violations = rule.check(graph)
        assert violations == []

    def test_file_does_not_exist_skipped(self, tmp_path: Path) -> None:
        specs_root = tmp_path / ".specs"
        specs_root.mkdir()
        graph = SpecGraph(
            features=[_make_feature(
                implementation_paths={"FR-001": ["src/missing.ts"]},
            )],
        )
        rule = R3_2_SpecAnchorMissing()
        rule.specs_root = specs_root
        violations = rule.check(graph)
        assert violations == []


# ---------------------------------------------------------------------------
# R4 — README / Disk sync
# ---------------------------------------------------------------------------


class TestR4_1_ReadmeFeatureMissing:
    def test_readme_references_missing_feature(self) -> None:
        graph = SpecGraph(
            readme_entries=["001-auth", "003-missing"],
            features=[_make_feature(dir_name="001-auth")],
        )
        violations = R4_1_ReadmeFeatureMissing().check(graph)
        assert len(violations) == 1
        assert violations[0].severity == Severity.ERROR
        assert "003-missing" in violations[0].message

    def test_all_readme_entries_exist(self) -> None:
        graph = SpecGraph(
            readme_entries=["001-auth"],
            features=[_make_feature(dir_name="001-auth")],
        )
        violations = R4_1_ReadmeFeatureMissing().check(graph)
        assert violations == []


class TestR4_2_DiskFeatureMissingReadme:
    def test_feature_not_in_readme(self) -> None:
        graph = SpecGraph(
            readme_entries=[],
            features=[_make_feature(dir_name="001-auth")],
        )
        violations = R4_2_DiskFeatureMissingReadme().check(graph)
        assert len(violations) == 1
        assert violations[0].severity == Severity.WARNING

    def test_feature_in_readme_is_valid(self) -> None:
        graph = SpecGraph(
            readme_entries=["001-auth"],
            features=[_make_feature(dir_name="001-auth")],
        )
        violations = R4_2_DiskFeatureMissingReadme().check(graph)
        assert violations == []


class TestR4_3_ReadmeStatusMismatch:
    def test_status_mismatch(self) -> None:
        graph = SpecGraph(
            readme_statuses={"001-auth": "Draft"},
            features=[_make_feature(dir_name="001-auth", status="Implemented")],
        )
        violations = R4_3_ReadmeStatusMismatch().check(graph)
        assert len(violations) == 1
        assert violations[0].severity == Severity.WARNING
        assert "Implemented" in violations[0].message
        assert "Draft" in violations[0].message

    def test_status_matches(self) -> None:
        graph = SpecGraph(
            readme_statuses={"001-auth": "Draft"},
            features=[_make_feature(dir_name="001-auth", status="Draft")],
        )
        violations = R4_3_ReadmeStatusMismatch().check(graph)
        assert violations == []

    def test_case_insensitive_match(self) -> None:
        graph = SpecGraph(
            readme_statuses={"001-auth": "draft"},
            features=[_make_feature(dir_name="001-auth", status="Draft")],
        )
        violations = R4_3_ReadmeStatusMismatch().check(graph)
        assert violations == []


# ---------------------------------------------------------------------------
# R5 — Stack / Preflight
# ---------------------------------------------------------------------------


class TestR5_1_StackNoPreflight:
    def test_tech_not_in_preflight(self) -> None:
        graph = SpecGraph(
            stack_technologies=["TypeScript", "Redis"],
            preflight_checks=["TypeScript compiler installed"],
        )
        violations = R5_1_StackNoPreflight().check(graph)
        assert len(violations) == 1
        assert violations[0].severity == Severity.INFO
        assert "Redis" in violations[0].message

    def test_all_techs_covered(self) -> None:
        graph = SpecGraph(
            stack_technologies=["TypeScript", "Redis"],
            preflight_checks=["TypeScript compiler installed", "Redis server running"],
        )
        violations = R5_1_StackNoPreflight().check(graph)
        assert violations == []

    def test_empty_stack_returns_nothing(self) -> None:
        graph = SpecGraph(
            stack_technologies=[],
            preflight_checks=["Something"],
        )
        violations = R5_1_StackNoPreflight().check(graph)
        assert violations == []

    def test_case_insensitive_check(self) -> None:
        graph = SpecGraph(
            stack_technologies=["PostgreSQL"],
            preflight_checks=["postgresql running"],
        )
        violations = R5_1_StackNoPreflight().check(graph)
        assert violations == []


# ---------------------------------------------------------------------------
# R6 — Changelog refs
# ---------------------------------------------------------------------------


class TestR6_1_ChangelogFeatureMissing:
    def test_changelog_ref_missing(self) -> None:
        graph = SpecGraph(
            changelog_refs=["001-auth", "099-phantom"],
            features=[_make_feature(dir_name="001-auth")],
        )
        violations = R6_1_ChangelogFeatureMissing().check(graph)
        assert len(violations) == 1
        assert violations[0].severity == Severity.WARNING
        assert "099-phantom" in violations[0].message

    def test_all_changelog_refs_valid(self) -> None:
        graph = SpecGraph(
            changelog_refs=["001-auth"],
            features=[_make_feature(dir_name="001-auth")],
        )
        violations = R6_1_ChangelogFeatureMissing().check(graph)
        assert violations == []

    def test_empty_changelog_returns_nothing(self) -> None:
        graph = SpecGraph(
            changelog_refs=[],
            features=[_make_feature()],
        )
        violations = R6_1_ChangelogFeatureMissing().check(graph)
        assert violations == []
