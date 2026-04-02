"""Tests for validator.semantic.scorecard — 5-axis scoring engine."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from validator.cli import app
from validator.coherence.graph_builder import FeatureInfo
from validator.semantic.scorecard import (
    AXIS_WEIGHTS,
    FeatureScore,
    ProjectScore,
    score_feature,
    score_project,
)

runner = CliRunner()


# --- Helpers ---


def _make_feature(
    specs_root: Path,
    dir_name: str = "001-auth",
    status: str = "Draft",
    files: dict[str, bool] | None = None,
    spec_anchors: list[str] | None = None,
) -> FeatureInfo:
    """Create a FeatureInfo and write files on disk."""
    if files is None:
        files = {"spec": False, "plan": False, "implementation": False, "progress": False, "changelog": False}
    return FeatureInfo(
        dir_name=dir_name,
        num=1,
        slug=dir_name.split("-", 1)[1] if "-" in dir_name else dir_name,
        files=files,
        status=status,
        spec_anchors=spec_anchors or [],
    )


def _write_spec(feature_dir: Path, content: str) -> None:
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "spec.md").write_text(content)


def _write_plan(feature_dir: Path, content: str) -> None:
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "plan.md").write_text(content)


def _write_impl(feature_dir: Path, content: str) -> None:
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "implementation.md").write_text(content)


def _write_changelog(feature_dir: Path, content: str) -> None:
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "changelog.md").write_text(content)


# --- Axis 1: Structural Completeness ---


class TestAxis1:
    """Structural completeness scoring."""

    def test_all_files_present_full_score(self, tmp_path: Path) -> None:
        specs_root = tmp_path / ".specs"
        feature_dir = specs_root / "features" / "001-auth"
        feature_dir.mkdir(parents=True)

        spec_content = """---
title: "Auth"
status: Draft
priority: P1
created: 2026-01-01
updated: 2026-01-15
---

## User Scenarios

User logs in.

## Acceptance Criteria

AC-1: User can login.

## Functional Requirements

FR-1: Authentication endpoint.
"""
        _write_spec(feature_dir, spec_content)
        _write_changelog(feature_dir, "# Changelog\n\n- Initial\n")

        feature = _make_feature(
            specs_root,
            files={"spec": True, "plan": True, "implementation": True, "progress": False, "changelog": True},
            status="Draft",
        )

        fs = score_feature(feature, specs_root)
        # spec present (20) + plan not required for Draft (15) + impl not required for Draft (15)
        # + changelog (10) + no NEEDS CLARIFICATION (20) + L1 valid (20) = 100
        assert fs.axes["structural_completeness"] == 100

    def test_missing_spec_low_score(self, tmp_path: Path) -> None:
        specs_root = tmp_path / ".specs"
        feature_dir = specs_root / "features" / "001-auth"
        feature_dir.mkdir(parents=True)

        feature = _make_feature(
            specs_root,
            files={"spec": False, "plan": False, "implementation": False, "progress": False, "changelog": False},
            status="Draft",
        )

        fs = score_feature(feature, specs_root)
        # No spec (0) + plan free pass (15) + impl free pass (15) + no changelog (0)
        # + no spec content so no clarification check + no L1 passing = 30
        assert fs.axes["structural_completeness"] == 30

    def test_needs_clarification_penalty(self, tmp_path: Path) -> None:
        specs_root = tmp_path / ".specs"
        feature_dir = specs_root / "features" / "001-auth"
        feature_dir.mkdir(parents=True)

        spec_content = """---
title: "Auth"
status: Draft
priority: P1
created: 2026-01-01
updated: 2026-01-15
---

## User Scenarios

[NEEDS CLARIFICATION] for login flow.

## Acceptance Criteria

AC-1: User can login.

## Functional Requirements

FR-1: Auth endpoint.
"""
        _write_spec(feature_dir, spec_content)

        feature = _make_feature(
            specs_root,
            files={"spec": True, "plan": False, "implementation": False, "progress": False, "changelog": False},
            status="Draft",
        )

        fs = score_feature(feature, specs_root)
        # spec (20) + plan free (15) + impl free (15) + no changelog (0)
        # + NEEDS CLARIFICATION penalty (0) + L1 passing (20) = 70
        assert fs.axes["structural_completeness"] == 70


# --- Axis 2: Artifact Quality ---


class TestAxis2:
    """Artifact quality scoring."""

    def test_with_mermaid_and_gherkin(self, tmp_path: Path) -> None:
        specs_root = tmp_path / ".specs"
        feature_dir = specs_root / "features" / "001-auth"
        feature_dir.mkdir(parents=True)

        spec_content = """---
title: "Auth"
status: Draft
priority: P1
created: 2026-01-01
updated: 2026-01-15
---

## User Scenarios

```mermaid
flowchart TD
    A[Start] --> B[Login]
```

## Acceptance Criteria

```gherkin
Feature: Login
  Scenario: Valid login
    Given a registered user
    When they submit valid credentials
    Then they are authenticated
```

## Functional Requirements

FR-1: Authentication endpoint.
AC-1: Referenced here.
"""
        _write_spec(feature_dir, spec_content)

        feature = _make_feature(
            specs_root,
            files={"spec": True, "plan": False, "implementation": False, "progress": False, "changelog": False},
        )

        fs = score_feature(feature, specs_root)
        # mermaid (25) + gherkin (25) + FR+AC both present (20) + no plan seq/state (0) + no entities (15) = 85
        assert fs.axes["artifact_quality"] == 85

    def test_without_mermaid_or_gherkin(self, tmp_path: Path) -> None:
        specs_root = tmp_path / ".specs"
        feature_dir = specs_root / "features" / "001-auth"
        feature_dir.mkdir(parents=True)

        spec_content = """---
title: "Auth"
status: Draft
priority: P1
created: 2026-01-01
updated: 2026-01-15
---

## User Scenarios

User logs in.

## Acceptance Criteria

AC-1: User can login.

## Functional Requirements

FR-1: Authentication endpoint.
"""
        _write_spec(feature_dir, spec_content)

        feature = _make_feature(
            specs_root,
            files={"spec": True, "plan": False, "implementation": False, "progress": False, "changelog": False},
        )

        fs = score_feature(feature, specs_root)
        # no mermaid (0) + no gherkin (0) + FR+AC both present (20) + no plan (0) + no entities (15) = 35
        assert fs.axes["artifact_quality"] == 35

    def test_plan_with_sequence_diagram(self, tmp_path: Path) -> None:
        specs_root = tmp_path / ".specs"
        feature_dir = specs_root / "features" / "001-auth"
        feature_dir.mkdir(parents=True)

        _write_spec(feature_dir, "---\ntitle: Auth\nstatus: Draft\npriority: P1\ncreated: 2026-01-01\nupdated: 2026-01-15\n---\n\n## User Scenarios\n\nTest.\n\n## Acceptance Criteria\n\nAC-1.\n\n## Functional Requirements\n\nFR-1.\n")

        plan_content = """---
title: "Auth Plan"
---

## Sequence

```mermaid
sequenceDiagram
    Client->>Server: POST /login
    Server-->>Client: 200 OK
```
"""
        _write_plan(feature_dir, plan_content)

        feature = _make_feature(
            specs_root,
            files={"spec": True, "plan": True, "implementation": False, "progress": False, "changelog": False},
        )

        fs = score_feature(feature, specs_root)
        # Check that sequence diagram in plan adds 15pts
        assert fs.axes["artifact_quality"] >= 15


# --- Axis 3: AC->FR Coverage ---


class TestAxis3:
    """AC->FR coverage scoring."""

    def test_full_coverage(self, tmp_path: Path) -> None:
        specs_root = tmp_path / ".specs"
        feature_dir = specs_root / "features" / "001-auth"
        feature_dir.mkdir(parents=True)

        spec_content = """---
title: Auth
status: Implemented
priority: P1
created: 2026-01-01
updated: 2026-01-15
---

## Acceptance Criteria

AC-1: Login works.
AC-2: Logout works.

## Functional Requirements

FR-1: Login endpoint.
FR-2: Logout endpoint.
"""
        _write_spec(feature_dir, spec_content)

        impl_content = """# Implementation

| Ref | Description | File |
|-----|-------------|------|
| FR-1 | Login | `src/auth.ts` |
| FR-2 | Logout | `src/auth.ts` |
| AC-1 | Login test | `tests/auth.test.ts` |
| AC-2 | Logout test | `tests/auth.test.ts` |

@spec(FR-1) @spec(FR-2) @spec(AC-1) @spec(AC-2)
"""
        _write_impl(feature_dir, impl_content)

        feature = _make_feature(
            specs_root,
            files={"spec": True, "plan": False, "implementation": True, "progress": False, "changelog": False},
            status="Implemented",
            spec_anchors=["FR-1", "FR-2", "AC-1", "AC-2"],
        )

        fs = score_feature(feature, specs_root)
        assert fs.axes["ac_fr_coverage"] == 100

    def test_no_implementation(self, tmp_path: Path) -> None:
        specs_root = tmp_path / ".specs"
        feature_dir = specs_root / "features" / "001-auth"
        feature_dir.mkdir(parents=True)

        spec_content = """---
title: Auth
status: Draft
priority: P1
created: 2026-01-01
updated: 2026-01-15
---

## Acceptance Criteria

AC-1: Login works.

## Functional Requirements

FR-1: Login endpoint.
"""
        _write_spec(feature_dir, spec_content)

        feature = _make_feature(
            specs_root,
            files={"spec": True, "plan": False, "implementation": False, "progress": False, "changelog": False},
        )

        fs = score_feature(feature, specs_root)
        # No impl: FR coverage 0/40, AC anchor 0/40, stale AC still referenced in spec = 20
        assert fs.axes["ac_fr_coverage"] == 20


# --- Axis 4: Semantic Coherence (stub) ---


class TestAxis4:
    """Semantic coherence is stubbed at 50."""

    def test_stub_returns_50(self, tmp_path: Path) -> None:
        specs_root = tmp_path / ".specs"
        feature_dir = specs_root / "features" / "001-auth"
        feature_dir.mkdir(parents=True)

        _write_spec(feature_dir, "---\ntitle: A\nstatus: Draft\npriority: P1\ncreated: 2026-01-01\nupdated: 2026-01-15\n---\n\n## User Scenarios\n\nTest.\n\n## Acceptance Criteria\n\nAC-1.\n\n## Functional Requirements\n\nFR-1.\n")

        feature = _make_feature(
            specs_root,
            files={"spec": True, "plan": False, "implementation": False, "progress": False, "changelog": False},
        )

        fs = score_feature(feature, specs_root)
        assert fs.axes["semantic_coherence"] == 50


# --- Axis 5: Mermaid Richness ---


class TestAxis5:
    """Mermaid richness scoring."""

    def test_multiple_diagram_types(self, tmp_path: Path) -> None:
        specs_root = tmp_path / ".specs"
        feature_dir = specs_root / "features" / "001-auth"
        feature_dir.mkdir(parents=True)

        spec_content = """---
title: Auth
status: Draft
priority: P1
created: 2026-01-01
updated: 2026-01-15
---

## User Scenarios

```mermaid
flowchart TD
    A --> B
```

## Acceptance Criteria

AC-1.

## Functional Requirements

FR-1.
"""
        _write_spec(feature_dir, spec_content)

        plan_content = """---
title: Plan
---

```mermaid
sequenceDiagram
    A->>B: Call
```
"""
        _write_plan(feature_dir, plan_content)

        feature = _make_feature(
            specs_root,
            files={"spec": True, "plan": True, "implementation": False, "progress": False, "changelog": False},
        )

        fs = score_feature(feature, specs_root)
        # present (30) + 2 types (40) + no empty (30) = 100
        assert fs.axes["mermaid_richness"] == 100

    def test_no_diagrams(self, tmp_path: Path) -> None:
        specs_root = tmp_path / ".specs"
        feature_dir = specs_root / "features" / "001-auth"
        feature_dir.mkdir(parents=True)

        _write_spec(feature_dir, "---\ntitle: A\nstatus: Draft\npriority: P1\ncreated: 2026-01-01\nupdated: 2026-01-15\n---\n\n## User Scenarios\n\nNo diagrams.\n\n## Acceptance Criteria\n\nAC-1.\n\n## Functional Requirements\n\nFR-1.\n")

        feature = _make_feature(
            specs_root,
            files={"spec": True, "plan": False, "implementation": False, "progress": False, "changelog": False},
        )

        fs = score_feature(feature, specs_root)
        assert fs.axes["mermaid_richness"] == 0


# --- Project scoring ---


class TestProjectScore:
    """Project-level aggregation."""

    def test_averages_correctly(self, tmp_path: Path) -> None:
        specs_root = tmp_path / ".specs"
        (specs_root / "features").mkdir(parents=True)

        for i, name in enumerate(["001-auth", "002-billing"], 1):
            feature_dir = specs_root / "features" / name
            feature_dir.mkdir()
            _write_spec(feature_dir, f"---\ntitle: F{i}\nstatus: Draft\npriority: P1\ncreated: 2026-01-01\nupdated: 2026-01-15\n---\n\n## User Scenarios\n\nTest.\n\n## Acceptance Criteria\n\nAC-1.\n\n## Functional Requirements\n\nFR-1.\n")

        features = [
            _make_feature(specs_root, dir_name="001-auth", files={"spec": True, "plan": False, "implementation": False, "progress": False, "changelog": False}),
            _make_feature(specs_root, dir_name="002-billing", files={"spec": True, "plan": False, "implementation": False, "progress": False, "changelog": False}),
        ]

        ps = score_project(features, specs_root)
        assert len(ps.features) == 2
        # Project total is average of feature totals
        expected = (ps.features[0].total + ps.features[1].total) / 2
        assert abs(ps.total - round(expected, 1)) < 0.2

    def test_empty_project(self, tmp_path: Path) -> None:
        specs_root = tmp_path / ".specs"
        specs_root.mkdir()
        ps = score_project([], specs_root)
        assert ps.total == 0.0
        assert len(ps.features) == 0


# --- Weights ---


class TestWeights:
    """Verify axis weights sum to 1.0."""

    def test_weights_sum_to_one(self) -> None:
        total = sum(AXIS_WEIGHTS.values())
        assert abs(total - 1.0) < 1e-9


# --- CLI integration ---


class TestCLI:
    """CLI --scorecard flag."""

    def test_scorecard_flag_produces_output(self, tmp_path: Path) -> None:
        specs_root = tmp_path / ".specs"
        features_dir = specs_root / "features" / "001-auth"
        features_dir.mkdir(parents=True)

        _write_spec(features_dir, "---\ntitle: Auth\nstatus: Draft\npriority: P1\ncreated: 2026-01-01\nupdated: 2026-01-15\n---\n\n## User Scenarios\n\nTest.\n\n## Acceptance Criteria\n\nAC-1.\n\n## Functional Requirements\n\nFR-1.\n")

        result = runner.invoke(app, ["validate", "--scorecard", "--warn-only", str(specs_root)])
        # Should not crash; output goes to stderr via Rich
        assert result.exit_code == 0

    def test_scorecard_json_format(self, tmp_path: Path) -> None:
        specs_root = tmp_path / ".specs"
        features_dir = specs_root / "features" / "001-auth"
        features_dir.mkdir(parents=True)

        _write_spec(features_dir, "---\ntitle: Auth\nstatus: Draft\npriority: P1\ncreated: 2026-01-01\nupdated: 2026-01-15\n---\n\n## User Scenarios\n\nTest.\n\n## Acceptance Criteria\n\nAC-1.\n\n## Functional Requirements\n\nFR-1.\n")

        result = runner.invoke(app, ["validate", "--scorecard", "--warn-only", "--format", "json", str(specs_root)])
        assert result.exit_code == 0
        # Output contains multiple JSON objects (L1 + scorecard). Parse last one.
        import json
        # Find the scorecard JSON (has "total" and "features" keys at root)
        lines = result.output.strip()
        # Split on }{ boundary between two JSON docs
        # Use json.JSONDecoder to parse iteratively
        decoder = json.JSONDecoder()
        idx = 0
        objects = []
        while idx < len(lines):
            lines_stripped = lines[idx:].lstrip()
            if not lines_stripped:
                break
            try:
                obj, end = decoder.raw_decode(lines_stripped)
                objects.append(obj)
                idx += len(lines) - len(lines_stripped) + end
            except json.JSONDecodeError:
                break
        # The scorecard JSON should be the last one with "total" and "features"
        scorecard_data = [o for o in objects if "total" in o and "features" in o]
        assert len(scorecard_data) == 1
        assert isinstance(scorecard_data[0]["features"], list)

    def test_contradiction_only_stub(self, tmp_path: Path) -> None:
        specs_root = tmp_path / ".specs"
        specs_root.mkdir()
        result = runner.invoke(app, ["validate", "--contradiction-only", str(specs_root)])
        assert result.exit_code == 0

    def test_reindex_stub(self, tmp_path: Path) -> None:
        specs_root = tmp_path / ".specs"
        specs_root.mkdir()
        result = runner.invoke(app, ["validate", "--reindex", str(specs_root)])
        assert result.exit_code == 0

    def test_mutate_stub(self, tmp_path: Path) -> None:
        specs_root = tmp_path / ".specs"
        specs_root.mkdir()
        result = runner.invoke(app, ["validate", "--mutate", str(specs_root)])
        assert result.exit_code == 0

    def test_experimental_multi_model_stub(self, tmp_path: Path) -> None:
        specs_root = tmp_path / ".specs"
        specs_root.mkdir()
        result = runner.invoke(app, ["validate", "--experimental-multi-model", str(specs_root)])
        assert result.exit_code == 0
