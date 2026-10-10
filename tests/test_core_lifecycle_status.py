"""Core status compatibility retains file requirements and normative byte protection."""

from __future__ import annotations

from dataclasses import replace
from datetime import date
from pathlib import Path

import frontmatter
import pytest

from tests.test_finalize import _implement_request, _make_specs_tree
from validator.coherence.graph_builder import build_graph
from validator.coherence.rules.r2_status_files import R2_1_RequiredFileAbsent, R2_3_InvalidStatus
from validator.coherence.rules.r4_readme_sync import R4_3_ReadmeStatusMismatch
from validator.expectations import parse_expectations
from validator.finalize import (
    FinalizeReceiptError,
    apply_finalization,
    verify_finalization,
    verify_finalize_receipt,
)
from validator.normative_identity import normative_hash
from validator.schemas.spec import SpecFrontmatter

ROOT = Path(__file__).parents[1]


@pytest.mark.parametrize("status", ["Planned", "In Progress"])
def test_official_lifecycle_producer_validates_and_preserves_body(
    tmp_path: Path, status: str
) -> None:
    """A real finalizer transition satisfies schema/R2/R4 without mutating normative bytes."""
    specs = _make_specs_tree(tmp_path)
    request = replace(_implement_request(), command="spec-plan", status=status)
    feature = specs / "features" / request.feature_slug
    spec = feature / "spec.md"
    (feature / "plan.md").write_text("# Plan\n", encoding="utf-8")
    # Start before planning so the Planned case exercises a real status/date transition.
    spec.write_text(spec.read_text().replace("Planned", "Draft"), encoding="utf-8")
    if status == "In Progress":
        # R2 still requires the implementation checkpoint at this lifecycle stage.
        (feature / "progress.md").write_text("# Progress\n", encoding="utf-8")
    before = spec.read_bytes()
    result = apply_finalization(tmp_path, request, today=date(2026, 10, 9))
    after = spec.read_bytes()
    expected = before.replace(b"status: Draft", f"status: {status}".encode(), 1)
    expected = expected.replace(b"- **Status:** Draft", f"- **Status:** {status}".encode(), 1)
    expected = expected.replace(b"updated: 2026-06-01", b"updated: 2026-10-09", 1)
    assert after == expected
    parsed = SpecFrontmatter.model_validate(frontmatter.load(str(spec)).metadata)
    assert parsed.status == status
    graph = build_graph(specs)
    assert graph.readme_statuses == {request.feature_slug: status}
    assert not R2_3_InvalidStatus().check(graph, specs)
    assert not R2_1_RequiredFileAbsent().check(graph, specs)
    assert not R4_3_ReadmeStatusMismatch().check(graph, specs)
    assert (
        verify_finalization(
            tmp_path, request.feature_slug, expected_command="spec-plan", run_id="verify-plan"
        ).verdict
        == "PASS"
    )
    assert normative_hash(before.decode(), lifecycle_document=True) == normative_hash(
        after.decode(), lifecycle_document=True
    )
    assert verify_finalize_receipt(result.receipt_path, project_root=tmp_path)
    # Content changes must invalidate both identity and the already-bound byte receipt.
    spec.write_bytes(after + b"\n## FR-999\nRetain exports forever.\n")
    assert normative_hash(spec.read_text(), lifecycle_document=True) != normative_hash(
        after.decode(), lifecycle_document=True
    )
    with pytest.raises(FinalizeReceiptError, match="sha256_mismatch"):
        verify_finalize_receipt(result.receipt_path, project_root=tmp_path)


@pytest.mark.parametrize("status,missing", [("Planned", "plan"), ("In Progress", "progress")])
def test_canonical_status_keeps_r2_required_files(
    tmp_path: Path, status: str, missing: str
) -> None:
    """Recognizing the status never exempts its required artifacts."""
    specs = _make_specs_tree(tmp_path)
    feature = specs / "features" / "004-notifications"
    spec = feature / "spec.md"
    spec.write_text(spec.read_text().replace("Planned", status), encoding="utf-8")
    if missing == "progress":
        # Isolate the missing progress requirement from the independent plan requirement.
        (feature / "plan.md").write_text("# Plan\n", encoding="utf-8")
    parsed = SpecFrontmatter.model_validate(frontmatter.load(str(spec)).metadata)
    assert parsed.status == status
    violations = R2_1_RequiredFileAbsent().check(build_graph(specs), specs)
    assert [violation.context["missing_file"] for violation in violations] == [missing]


def test_readme_status_drift_remains_a_failed_finalization(tmp_path: Path) -> None:
    """The metadata permission cannot relax README/Spec status coherence."""
    specs = _make_specs_tree(tmp_path)
    request = replace(_implement_request(), command="spec-plan", status="Planned")
    apply_finalization(tmp_path, request)
    readme = specs / "README.md"
    readme.write_text(readme.read_text().replace("Planned", "Approved"))
    violations = R4_3_ReadmeStatusMismatch().check(build_graph(specs), specs)
    assert [violation.rule_id for violation in violations] == ["R4.3"]
    result = verify_finalization(tmp_path, request.feature_slug, run_id="mismatch")
    assert result.verdict == "FAIL"
    assert "R4.3" in [violation.rule_id for violation in result.violations]


def test_plan_expectations_preserve_explicit_metadata_only_boundary() -> None:
    """The actual parser exposes the bounded permission to contract consumers."""
    expectations = parse_expectations(ROOT / ".agent-sync/skills/spec-plan/expectations.md")
    effects = expectations.prose_sections["4. Filesystem Effects"]
    assert "only recognized lifecycle `status` and `updated` slots" in effects
    assert "official `livespec finalize apply`" in effects
    forbidden = effects.split("**forbidden:**", 1)[1]
    for protected in ("normative body", "FR/AC", "IDs", "headings/title", "`created`", "comments"):
        assert protected in forbidden
    assert "Missing, duplicate or malformed lifecycle slots remain blocking" in forbidden


def test_installed_and_canonical_status_documentation_match_schema() -> None:
    """Both system descriptions retain the same strict producer vocabulary."""
    expected = (
        "- **Status** — Draft | Planned | In Progress | Approved | Implemented"
        " | Deprecated | Review"
    )
    for relative in ("system/spec-system.md", ".specs/spec-system.md"):
        assert expected in (ROOT / relative).read_text()


@pytest.mark.parametrize("status", ["Planned", "In Progress"])
def test_readme_retains_legacy_feature_first_statuses(tmp_path: Path, status: str) -> None:
    """Canonical support keeps the existing linked and plain legacy row formats."""
    specs = _make_specs_tree(tmp_path)
    (specs / "README.md").write_text(
        f"| [004-notifications](features/004-notifications/) | {status} |\n| 005-old | {status} |\n"
    )
    assert build_graph(specs).readme_statuses == {"004-notifications": status, "005-old": status}


@pytest.mark.parametrize(
    "row",
    [
        "| # | Feature | Status | Created | Updated | Spec |",
        "| 2026-10-09 | Feature | [spec](features/004-notifications/spec.md) |",
        "| 005 | Title | Planned | 2026-01-01 | 2026-01-01 | "
        "[spec](features/004-notifications/spec.md) |",
        "| 004 | Title | Planned | 2026-01-01 | 2026-01-01 | "
        "[spec](features/004-notifications/spec.md) [other](features/005-other/spec.md) |",
    ],
)
def test_unrelated_or_inconsistent_rows_cannot_supply_a_feature_status(
    tmp_path: Path, row: str
) -> None:
    """An activity date or ambiguous identity cannot stand in for the feature row."""
    specs = _make_specs_tree(tmp_path)
    (specs / "README.md").write_text(row + "\n")
    assert build_graph(specs).readme_statuses == {}


@pytest.mark.parametrize(
    "opening,closing",
    [
        ("```markdown", "```"),
        ("~~~~markdown", "~~~~"),
        ("````markdown\n```", "```\n````"),
        ("<!--", "-->"),
        ("<!-- example", "-->"),
        ("```markdown\n    ```", "```"),
        ("```markdown\n\t```", "```"),
    ],
)
def test_examples_cannot_mask_a_real_canonical_readme_status_mismatch(
    tmp_path: Path, opening: str, closing: str
) -> None:
    """R1: an example with the spec status must never certify a divergent real registry."""
    specs = _make_specs_tree(tmp_path)
    request = replace(_implement_request(), command="spec-plan", status="Planned")
    apply_finalization(tmp_path, request)
    readme = specs / "README.md"
    divergent = readme.read_text().replace("Planned", "Approved")
    example = (
        "| 004 | Notifications | Planned | 2026-06-01 | 2026-10-09 | "
        "[spec](features/004-notifications/spec.md) |"
    )
    readme.write_text(divergent + f"\n{opening}\n{example}\n{closing}\n")
    graph = build_graph(specs)
    assert graph.readme_statuses == {request.feature_slug: "Approved"}
    assert [v.rule_id for v in R4_3_ReadmeStatusMismatch().check(graph, specs)] == ["R4.3"]
    result = verify_finalization(tmp_path, request.feature_slug, run_id="example-mismatch")
    assert result.verdict == "FAIL"
    assert "R4.3" in [violation.rule_id for violation in result.violations]


@pytest.mark.parametrize("indent", ["    ", "\t", "  \t"])
def test_indented_examples_cannot_mask_a_real_registry_status(tmp_path: Path, indent: str) -> None:
    """R1: indented Markdown code stays inert without an explicit fence."""
    specs = _make_specs_tree(tmp_path)
    request = replace(_implement_request(), command="spec-plan", status="Planned")
    apply_finalization(tmp_path, request)
    readme = specs / "README.md"
    example = (
        f"{indent}| 004 | Notifications | Planned | 2026-06-01 | 2026-10-09 | "
        "[spec](features/004-notifications/spec.md) |\n"
    )
    readme.write_text(readme.read_text().replace("Planned", "Approved") + "\n" + example)
    graph = build_graph(specs)
    assert graph.readme_statuses == {request.feature_slug: "Approved"}
    assert [v.rule_id for v in R4_3_ReadmeStatusMismatch().check(graph, specs)] == ["R4.3"]
    assert verify_finalization(tmp_path, request.feature_slug, run_id="indent").verdict == "FAIL"
