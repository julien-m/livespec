# @spec(AC-010)
# @spec(AC-011)
# @spec(AC-012)

"""Tests for each individual coherence rule — pure dataclass construction, no disk I/O."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path

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
from validator.coherence.rules.r7_conventions_gates import (
    R7_1_ConventionsGatesMissingOrStale,
    R7_2_ConventionsExclusionTooBroad,
    R7_3_ConventionsRulebookSourcesStale,
)
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
        files=files
        or {
            "spec": True,
            "plan": True,
            "implementation": False,
            "progress": False,
            "changelog": False,
        },
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
        violations = R1_1_RoadmapFeatureMissing().check(graph, Path("."))
        assert len(violations) == 1
        assert violations[0].severity == Severity.ERROR
        assert "001-auth" in violations[0].message

    def test_checked_link_to_existing_feature(self) -> None:
        graph = SpecGraph(
            roadmap=[_make_roadmap_item(checked=True, link="features/001-auth/")],
            features=[_make_feature()],
        )
        violations = R1_1_RoadmapFeatureMissing().check(graph, Path("."))
        assert violations == []

    def test_unchecked_item_ignored(self) -> None:
        graph = SpecGraph(
            roadmap=[_make_roadmap_item(checked=False, link="features/001-auth/")],
            features=[],
        )
        violations = R1_1_RoadmapFeatureMissing().check(graph, Path("."))
        assert violations == []

    def test_no_link_ignored(self) -> None:
        graph = SpecGraph(
            roadmap=[_make_roadmap_item(checked=True, link=None)],
            features=[],
        )
        violations = R1_1_RoadmapFeatureMissing().check(graph, Path("."))
        assert violations == []


class TestR1_2_OrphanFeature:
    def test_feature_not_in_roadmap(self) -> None:
        graph = SpecGraph(
            roadmap=[],
            features=[_make_feature(dir_name="001-auth", slug="auth")],
        )
        violations = R1_2_OrphanFeature().check(graph, Path("."))
        assert len(violations) == 1
        assert violations[0].severity == Severity.WARNING

    def test_feature_in_roadmap_via_link(self) -> None:
        graph = SpecGraph(
            roadmap=[_make_roadmap_item(link="features/001-auth/")],
            features=[_make_feature()],
        )
        violations = R1_2_OrphanFeature().check(graph, Path("."))
        assert violations == []

    def test_feature_in_roadmap_via_slug(self) -> None:
        # roadmap_refs collects item.slug, so "001-auth" matches feature dir_name "001-auth"
        graph = SpecGraph(
            roadmap=[_make_roadmap_item(slug="001-auth", link=None)],
            features=[_make_feature(dir_name="001-auth", slug="auth")],
        )
        violations = R1_2_OrphanFeature().check(graph, Path("."))
        assert violations == []

    def test_feature_truly_orphan(self) -> None:
        graph = SpecGraph(
            roadmap=[_make_roadmap_item(slug="other", link=None, name="Other")],
            features=[_make_feature(dir_name="001-auth", slug="auth")],
        )
        violations = R1_2_OrphanFeature().check(graph, Path("."))
        assert len(violations) == 1


class TestR1_3_StatusRoadmapMismatch:
    def test_implemented_but_unchecked(self) -> None:
        graph = SpecGraph(
            roadmap=[_make_roadmap_item(checked=False, link="features/001-auth/")],
            features=[_make_feature(status="Implemented")],
        )
        violations = R1_3_StatusRoadmapMismatch().check(graph, Path("."))
        assert len(violations) == 1
        assert violations[0].severity == Severity.ERROR
        assert "Implemented" in violations[0].message

    def test_draft_and_checked_is_valid(self) -> None:
        graph = SpecGraph(
            roadmap=[_make_roadmap_item(checked=True, link="features/001-auth/")],
            features=[_make_feature(status="Draft")],
        )
        violations = R1_3_StatusRoadmapMismatch().check(graph, Path("."))
        assert violations == []

    def test_implemented_and_checked_is_valid(self) -> None:
        graph = SpecGraph(
            roadmap=[_make_roadmap_item(checked=True, link="features/001-auth/")],
            features=[_make_feature(status="Implemented")],
        )
        violations = R1_3_StatusRoadmapMismatch().check(graph, Path("."))
        assert violations == []

    def test_deprecated_status_skipped(self) -> None:
        graph = SpecGraph(
            roadmap=[_make_roadmap_item(checked=False, link="features/001-auth/")],
            features=[_make_feature(status="Deprecated")],
        )
        violations = R1_3_StatusRoadmapMismatch().check(graph, Path("."))
        assert violations == []


class TestR1_4_CheckedNoLink:
    def test_checked_no_link(self) -> None:
        graph = SpecGraph(
            roadmap=[_make_roadmap_item(checked=True, link=None)],
        )
        violations = R1_4_CheckedNoLink().check(graph, Path("."))
        assert len(violations) == 1
        assert violations[0].severity == Severity.WARNING

    def test_checked_with_non_feature_link(self) -> None:
        graph = SpecGraph(
            roadmap=[_make_roadmap_item(checked=True, link="https://example.com")],
        )
        violations = R1_4_CheckedNoLink().check(graph, Path("."))
        assert len(violations) == 1
        assert violations[0].severity == Severity.WARNING

    def test_checked_with_feature_link_is_valid(self) -> None:
        graph = SpecGraph(
            roadmap=[_make_roadmap_item(checked=True, link="features/001-auth/")],
        )
        violations = R1_4_CheckedNoLink().check(graph, Path("."))
        assert violations == []

    def test_unchecked_ignored(self) -> None:
        graph = SpecGraph(
            roadmap=[_make_roadmap_item(checked=False, link=None)],
        )
        violations = R1_4_CheckedNoLink().check(graph, Path("."))
        assert violations == []


# ---------------------------------------------------------------------------
# R2 — Status / Files
# ---------------------------------------------------------------------------


class TestR2_1_RequiredFileAbsent:
    def test_planned_missing_plan(self) -> None:
        graph = SpecGraph(
            features=[
                _make_feature(
                    status="Planned",
                    files={
                        "spec": True,
                        "plan": False,
                        "implementation": False,
                        "progress": False,
                        "changelog": False,
                    },
                )
            ],
        )
        violations = R2_1_RequiredFileAbsent().check(graph, Path("."))
        assert len(violations) == 1
        assert violations[0].severity == Severity.ERROR
        assert "plan.md" in violations[0].message

    def test_planned_with_all_files_is_valid(self) -> None:
        graph = SpecGraph(
            features=[
                _make_feature(
                    status="Planned",
                    files={
                        "spec": True,
                        "plan": True,
                        "implementation": False,
                        "progress": False,
                        "changelog": False,
                    },
                )
            ],
        )
        violations = R2_1_RequiredFileAbsent().check(graph, Path("."))
        assert violations == []

    def test_no_status_skipped(self) -> None:
        graph = SpecGraph(features=[_make_feature(status=None)])
        violations = R2_1_RequiredFileAbsent().check(graph, Path("."))
        assert violations == []


class TestR2_2_AdvancedFileForLowStatus:
    def test_draft_with_implementation(self) -> None:
        graph = SpecGraph(
            features=[
                _make_feature(
                    status="Draft",
                    files={
                        "spec": True,
                        "plan": False,
                        "implementation": True,
                        "progress": False,
                        "changelog": False,
                    },
                )
            ],
        )
        violations = R2_2_AdvancedFileForLowStatus().check(graph, Path("."))
        assert len(violations) == 1
        assert violations[0].severity == Severity.WARNING

    def test_draft_without_implementation_is_valid(self) -> None:
        graph = SpecGraph(
            features=[
                _make_feature(
                    status="Draft",
                    files={
                        "spec": True,
                        "plan": False,
                        "implementation": False,
                        "progress": False,
                        "changelog": False,
                    },
                )
            ],
        )
        violations = R2_2_AdvancedFileForLowStatus().check(graph, Path("."))
        assert violations == []

    def test_implemented_with_implementation_is_valid(self) -> None:
        graph = SpecGraph(
            features=[
                _make_feature(
                    status="Implemented",
                    files={
                        "spec": True,
                        "plan": True,
                        "implementation": True,
                        "progress": False,
                        "changelog": False,
                    },
                )
            ],
        )
        violations = R2_2_AdvancedFileForLowStatus().check(graph, Path("."))
        assert violations == []


class TestR2_3_InvalidStatus:
    def test_unknown_status(self) -> None:
        graph = SpecGraph(features=[_make_feature(status="Unknown")])
        violations = R2_3_InvalidStatus().check(graph, Path("."))
        assert len(violations) == 1
        assert violations[0].severity == Severity.ERROR
        assert "Unknown" in violations[0].message

    def test_valid_statuses_pass(self) -> None:
        valid_statuses = (
            "Draft",
            "Planned",
            "In Progress",
            "Approved",
            "Implemented",
            "Deprecated",
            "Review",
        )
        for status in valid_statuses:
            graph = SpecGraph(features=[_make_feature(status=status)])
            violations = R2_3_InvalidStatus().check(graph, Path("."))
            assert violations == [], f"Status '{status}' should be valid"

    def test_none_status_skipped(self) -> None:
        graph = SpecGraph(features=[_make_feature(status=None)])
        violations = R2_3_InvalidStatus().check(graph, Path("."))
        assert violations == []


# ---------------------------------------------------------------------------
# R3 — Spec Anchors (needs specs_root for filesystem access)
# ---------------------------------------------------------------------------


class TestR3_1_SourceFileNotFound:
    def test_missing_source_file(self, tmp_path: Path) -> None:
        specs_root = tmp_path / ".specs"
        specs_root.mkdir()
        graph = SpecGraph(
            features=[
                _make_feature(
                    implementation_paths={"FR-001": ["src/auth/login.ts"]},
                )
            ],
        )
        violations = R3_1_SourceFileNotFound().check(graph, specs_root)
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
            features=[
                _make_feature(
                    implementation_paths={"FR-001": ["src/auth/login.ts"]},
                )
            ],
        )
        violations = R3_1_SourceFileNotFound().check(graph, specs_root)
        assert violations == []

    def test_existing_source_file_with_line_suffix(self, tmp_path: Path) -> None:
        specs_root = tmp_path / ".specs"
        specs_root.mkdir()
        agent_file = tmp_path / "agents" / "livespec-supervisor.md"
        agent_file.parent.mkdir(parents=True)
        agent_file.write_text("# Supervisor\n")
        graph = SpecGraph(
            features=[
                _make_feature(
                    implementation_paths={"AC-001": ["agents/livespec-supervisor.md:154"]},
                )
            ],
        )

        violations = R3_1_SourceFileNotFound().check(graph, specs_root)

        assert violations == []

    def test_existing_source_file_glob(self, tmp_path: Path) -> None:
        specs_root = tmp_path / ".specs"
        specs_root.mkdir()
        skill_file = tmp_path / ".agent-sync" / "skills" / "spec-test" / "expectations.md"
        skill_file.parent.mkdir(parents=True)
        skill_file.write_text("# Expectations\n")
        graph = SpecGraph(
            features=[
                _make_feature(
                    implementation_paths={"FR-001": [".agent-sync/skills/*/expectations.md"]},
                )
            ],
        )

        violations = R3_1_SourceFileNotFound().check(graph, specs_root)

        assert violations == []

    def test_no_implementation_paths_is_valid(self, tmp_path: Path) -> None:
        specs_root = tmp_path / ".specs"
        specs_root.mkdir()
        graph = SpecGraph(features=[_make_feature()])
        violations = R3_1_SourceFileNotFound().check(graph, specs_root)
        assert violations == []


class TestR3_2_SpecAnchorMissing:
    def test_anchor_not_in_source(self, tmp_path: Path) -> None:
        specs_root = tmp_path / ".specs"
        specs_root.mkdir()
        src_file = tmp_path / "src" / "auth.ts"
        src_file.parent.mkdir(parents=True)
        src_file.write_text("// no anchor here\nfunction login() {}\n")
        graph = SpecGraph(
            features=[
                _make_feature(
                    implementation_paths={"FR-001": ["src/auth.ts"]},
                )
            ],
        )
        violations = R3_2_SpecAnchorMissing().check(graph, specs_root)
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
            features=[
                _make_feature(
                    implementation_paths={"FR-001": ["src/auth.ts"]},
                )
            ],
        )
        violations = R3_2_SpecAnchorMissing().check(graph, specs_root)
        assert violations == []

    def test_file_does_not_exist_skipped(self, tmp_path: Path) -> None:
        specs_root = tmp_path / ".specs"
        specs_root.mkdir()
        graph = SpecGraph(
            features=[
                _make_feature(
                    implementation_paths={"FR-001": ["src/missing.ts"]},
                )
            ],
        )
        violations = R3_2_SpecAnchorMissing().check(graph, specs_root)
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
        violations = R4_1_ReadmeFeatureMissing().check(graph, Path("."))
        assert len(violations) == 1
        assert violations[0].severity == Severity.ERROR
        assert "003-missing" in violations[0].message

    def test_all_readme_entries_exist(self) -> None:
        graph = SpecGraph(
            readme_entries=["001-auth"],
            features=[_make_feature(dir_name="001-auth")],
        )
        violations = R4_1_ReadmeFeatureMissing().check(graph, Path("."))
        assert violations == []


class TestR4_2_DiskFeatureMissingReadme:
    def test_feature_not_in_readme(self) -> None:
        graph = SpecGraph(
            readme_entries=[],
            features=[_make_feature(dir_name="001-auth")],
        )
        violations = R4_2_DiskFeatureMissingReadme().check(graph, Path("."))
        assert len(violations) == 1
        assert violations[0].severity == Severity.WARNING

    def test_feature_in_readme_is_valid(self) -> None:
        graph = SpecGraph(
            readme_entries=["001-auth"],
            features=[_make_feature(dir_name="001-auth")],
        )
        violations = R4_2_DiskFeatureMissingReadme().check(graph, Path("."))
        assert violations == []


class TestR4_3_ReadmeStatusMismatch:
    def test_status_mismatch(self) -> None:
        graph = SpecGraph(
            readme_statuses={"001-auth": "Draft"},
            features=[_make_feature(dir_name="001-auth", status="Implemented")],
        )
        violations = R4_3_ReadmeStatusMismatch().check(graph, Path("."))
        assert len(violations) == 1
        assert violations[0].severity == Severity.WARNING
        assert "Implemented" in violations[0].message
        assert "Draft" in violations[0].message

    def test_status_matches(self) -> None:
        graph = SpecGraph(
            readme_statuses={"001-auth": "Draft"},
            features=[_make_feature(dir_name="001-auth", status="Draft")],
        )
        violations = R4_3_ReadmeStatusMismatch().check(graph, Path("."))
        assert violations == []

    def test_case_insensitive_match(self) -> None:
        graph = SpecGraph(
            readme_statuses={"001-auth": "draft"},
            features=[_make_feature(dir_name="001-auth", status="Draft")],
        )
        violations = R4_3_ReadmeStatusMismatch().check(graph, Path("."))
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
        violations = R5_1_StackNoPreflight().check(graph, Path("."))
        assert len(violations) == 1
        assert violations[0].severity == Severity.INFO
        assert "Redis" in violations[0].message

    def test_all_techs_covered(self) -> None:
        graph = SpecGraph(
            stack_technologies=["TypeScript", "Redis"],
            preflight_checks=["TypeScript compiler installed", "Redis server running"],
        )
        violations = R5_1_StackNoPreflight().check(graph, Path("."))
        assert violations == []

    def test_empty_stack_returns_nothing(self) -> None:
        graph = SpecGraph(
            stack_technologies=[],
            preflight_checks=["Something"],
        )
        violations = R5_1_StackNoPreflight().check(graph, Path("."))
        assert violations == []

    def test_case_insensitive_check(self) -> None:
        graph = SpecGraph(
            stack_technologies=["PostgreSQL"],
            preflight_checks=["postgresql running"],
        )
        violations = R5_1_StackNoPreflight().check(graph, Path("."))
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
        violations = R6_1_ChangelogFeatureMissing().check(graph, Path("."))
        assert len(violations) == 1
        assert violations[0].severity == Severity.WARNING
        assert "099-phantom" in violations[0].message

    def test_all_changelog_refs_valid(self) -> None:
        graph = SpecGraph(
            changelog_refs=["001-auth"],
            features=[_make_feature(dir_name="001-auth")],
        )
        violations = R6_1_ChangelogFeatureMissing().check(graph, Path("."))
        assert violations == []

    def test_empty_changelog_returns_nothing(self) -> None:
        graph = SpecGraph(
            changelog_refs=[],
            features=[_make_feature()],
        )
        violations = R6_1_ChangelogFeatureMissing().check(graph, Path("."))
        assert violations == []


# ---------------------------------------------------------------------------
# R7 — Conventions Gates
# ---------------------------------------------------------------------------


def _write_constitution(specs_root: Path, text: str = "max file lines and ruff\n") -> None:
    specs_root.mkdir(parents=True, exist_ok=True)
    (specs_root / "constitution.md").write_text(text, encoding="utf-8")


class TestR7_1_ConventionsGatesMissingOrStale:
    def test_constitution_declares_limits_but_gates_absent(self, tmp_path: Path) -> None:
        specs_root = tmp_path / ".specs"
        _write_constitution(specs_root)

        violations = R7_1_ConventionsGatesMissingOrStale().check(SpecGraph(), specs_root)

        assert len(violations) == 1
        assert violations[0].severity == Severity.ERROR
        assert "conventions-gates.yaml" in violations[0].message

    def test_constitution_hash_stale(self, tmp_path: Path) -> None:
        specs_root = tmp_path / ".specs"
        _write_constitution(specs_root)
        (specs_root / "conventions-gates.yaml").write_text(
            """\
schema_version: 1
generated_from:
  constitution: .specs/constitution.md
  constitution_sha256: 0000000000000000000000000000000000000000000000000000000000000000
  stack: .specs/stacks/_default.md
commands: {}
builtin: {}
coverage: {}
exclusions: []
scope: repo
""",
            encoding="utf-8",
        )

        violations = R7_1_ConventionsGatesMissingOrStale().check(SpecGraph(), specs_root)

        assert len(violations) == 1
        assert violations[0].severity == Severity.ERROR
        assert "constitution_sha256" in violations[0].message

    def test_canonical_constitution_takes_precedence_over_declared_path(
        self,
        tmp_path: Path,
    ) -> None:
        specs_root = tmp_path / ".specs"
        _write_constitution(specs_root, text="ruff limits changed\n")
        declared = tmp_path / "custom-constitution.md"
        declared.write_text("ruff limits old\n", encoding="utf-8")
        declared_hash = sha256(declared.read_bytes()).hexdigest()
        (specs_root / "conventions-gates.yaml").write_text(
            f"""\
schema_version: 1
generated_from:
  constitution: custom-constitution.md
  constitution_sha256: {declared_hash}
  stack: .specs/stacks/_default.md
commands: {{}}
builtin: {{}}
coverage: {{}}
exclusions: []
scope: repo
""",
            encoding="utf-8",
        )

        violations = R7_1_ConventionsGatesMissingOrStale().check(SpecGraph(), specs_root)

        assert len(violations) == 1
        assert violations[0].severity == Severity.ERROR
        assert "constitution_sha256" in violations[0].message


class TestR7_2_ConventionsExclusionTooBroad:
    def test_exclusion_matching_more_than_30_percent_of_repo_is_error(self, tmp_path: Path) -> None:
        specs_root = tmp_path / ".specs"
        specs_root.mkdir(parents=True)
        for path in (
            tmp_path / "src" / "a.py",
            tmp_path / "src" / "b.py",
            tmp_path / "src" / "c.py",
            tmp_path / "tests" / "test_a.py",
        ):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("x\n", encoding="utf-8")
        (specs_root / "conventions-gates.yaml").write_text(
            """\
schema_version: 1
generated_from:
  constitution: .specs/constitution.md
  constitution_sha256: 0000000000000000000000000000000000000000000000000000000000000000
  stack: .specs/stacks/_default.md
commands: {}
builtin: {}
coverage: {}
exclusions:
  - src/**
scope: repo
""",
            encoding="utf-8",
        )

        violations = R7_2_ConventionsExclusionTooBroad().check(SpecGraph(), specs_root)

        assert len(violations) == 1
        assert violations[0].severity == Severity.ERROR
        assert "src/**" in violations[0].message

    def test_standard_tooling_exclusion_is_ignored(self, tmp_path: Path) -> None:
        specs_root = tmp_path / ".specs"
        specs_root.mkdir(parents=True)
        for path in (
            tmp_path / ".venv" / "lib" / "a.py",
            tmp_path / ".venv" / "lib" / "b.py",
            tmp_path / ".venv" / "lib" / "c.py",
            tmp_path / "src" / "app.py",
        ):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("x\n", encoding="utf-8")
        (specs_root / "conventions-gates.yaml").write_text(
            """\
schema_version: 1
generated_from:
  constitution: .specs/constitution.md
  constitution_sha256: 0000000000000000000000000000000000000000000000000000000000000000
  stack: .specs/stacks/_default.md
commands: {}
builtin: {}
coverage: {}
exclusions:
  - .venv/**
scope: repo
""",
            encoding="utf-8",
        )

        violations = R7_2_ConventionsExclusionTooBroad().check(SpecGraph(), specs_root)

        assert violations == []

    def test_exclusion_ratio_ignores_tooling_files_in_denominator(self, tmp_path: Path) -> None:
        specs_root = tmp_path / ".specs"
        specs_root.mkdir(parents=True)
        for index in range(20):
            path = tmp_path / ".venv" / "lib" / f"dep_{index}.py"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("x\n", encoding="utf-8")
        for path in (
            tmp_path / "src" / "a.py",
            tmp_path / "src" / "b.py",
            tmp_path / "tests" / "test_a.py",
        ):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("x\n", encoding="utf-8")
        (specs_root / "conventions-gates.yaml").write_text(
            """\
schema_version: 1
generated_from:
  constitution: .specs/constitution.md
  constitution_sha256: 0000000000000000000000000000000000000000000000000000000000000000
  stack: .specs/stacks/_default.md
commands: {}
builtin: {}
coverage: {}
exclusions:
  - src/**
scope: repo
""",
            encoding="utf-8",
        )

        violations = R7_2_ConventionsExclusionTooBroad().check(SpecGraph(), specs_root)

        assert len(violations) == 1
        assert "src/**" in violations[0].message


class TestR7_3_ConventionsRulebookSourcesStale:
    def test_rulebook_source_hash_stale(self, tmp_path: Path) -> None:
        specs_root = tmp_path / ".specs"
        specs_root.mkdir(parents=True)
        ai_root = tmp_path / "ai"
        source = ai_root / "code-conventions" / "general.md"
        source.parent.mkdir(parents=True)
        source.write_text("# General\ncurrent\n", encoding="utf-8")
        conventions = tmp_path / ".conventions"
        conventions.mkdir()
        (conventions / "index.md").write_text(
            f"""\
# Conventions
> `$AIRESOURCES` = `{ai_root.as_posix()}`

## code [code]
→ $AIRESOURCES/code-conventions/general.md
""",
            encoding="utf-8",
        )
        (specs_root / "conventions-rulebook.yaml").write_text(
            """\
schema_version: 1
compiled_at: "2026-06-13T00:00:00+00:00"
sources:
  - path: $AIRESOURCES/code-conventions/general.md
    sha256: "0000000000000000000000000000000000000000000000000000000000000000"
rules: []
unenforceable: []
waivers: []
""",
            encoding="utf-8",
        )

        violations = R7_3_ConventionsRulebookSourcesStale().check(SpecGraph(), specs_root)

        assert len(violations) == 1
        assert violations[0].severity == Severity.ERROR
        assert "$AIRESOURCES/code-conventions/general.md" in violations[0].message
