"""Actual finalize writes preserve execution proof, while normative edits invalidate it."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from tests.execution_evidence_support import AC, FEATURE, run
from tests.execution_evidence_support import project as project
from validator.execution_evidence import verify_execution_receipt
from validator.execution_scope import source_manifest
from validator.finalize import ApplyRequest, apply_finalization, verify_finalize_receipt


def _registries(root: Path) -> None:
    specs = root / ".specs"
    (specs / ".LOCK").touch()  # Real projects ignore this pre-existing registry lock.
    (specs / "README.md").write_text(
        "# Registry\n\nRetention must be bounded. Read [policy](policy.md).\n\n"
        "> Last updated: 2026-10-16\n\n<!-- readme:features:start -->\n"
        "| # | Feature | Status | Created | Updated | Spec |\n"
        "|---|---|---|---|---|---|\n"
        f"| 001 | Addition | Draft | 2026-10-16 | 2026-10-16 | "
        f"[spec](features/{FEATURE}/spec.md) |\n<!-- readme:features:end -->\n\n"
        "<!-- readme:activity:start -->\n| Date | Type | Description |\n"
        "|---|---|---|\n<!-- readme:activity:end -->\n"
    )
    (specs / "changelog.md").write_text("# Changelog\n\nManual retention decision.\n")
    (specs / "policy.md").write_text("Retention: 24 hours.\n")
    (specs / "livespec.lock").write_text('{"runtime_id":"frozen"}\n')
    feature = specs / "features" / FEATURE
    (feature / "plan.md").write_text(
        "# Plan\nRead [registry](../../README.md) and [history](../../changelog.md).\n"
    )


def _finalize(root: Path) -> None:
    result = apply_finalization(
        root,
        ApplyRequest(
            FEATURE, "spec-implement", None, "Feature: Addition", "Addition implemented", "test"
        ),
        today=date(2026, 10, 17),
    )
    assert verify_finalize_receipt(result.receipt_path, project_root=root).verdict == "PASS"


# @spec FR-011: generated registry references cannot stale actual execution
# — .specs/features/078-requirement-evidence-integrity/spec.md#fr-011
def test_actual_finalize_preserves_referenced_execution_inputs(project: Path) -> None:
    _registries(project)
    before = source_manifest(project, FEATURE)
    receipt = run(project)
    assert verify_execution_receipt(receipt, project, FEATURE, (AC,)).valid
    _finalize(project)
    assert source_manifest(project, FEATURE) == before
    result = verify_execution_receipt(receipt, project, FEATURE, (AC,))
    assert result.valid, result.gaps
    assert result.certified_acs == [AC]


def test_registry_prose_and_linked_normative_edits_remain_stale(project: Path) -> None:
    _registries(project)
    receipt = run(project)
    for relative in (".specs/README.md", ".specs/changelog.md", ".specs/policy.md"):
        path = project / relative
        original = path.read_bytes()
        path.write_bytes(original + b"Retention: forever.\n")
        result = verify_execution_receipt(receipt, project, FEATURE, (AC,))
        assert not result.valid, relative
        assert any("stale" in gap for gap in result.gaps), result.gaps
        path.write_bytes(original)
    assert verify_execution_receipt(receipt, project, FEATURE, (AC,)).valid


def test_product_tests_config_and_registry_identity_remain_bound(project: Path) -> None:
    _registries(project)
    before = source_manifest(project, FEATURE)
    for relative in (
        "app.py", "test_app.py", ".specs/livespec.lock", ".specs/features/001-add/spec.md"
    ):
        path = project / relative
        original = path.read_bytes()
        path.write_bytes(original + b"# changed\n")
        assert source_manifest(project, FEATURE) != before, relative
        path.write_bytes(original)
    path = project / ".specs/README.md"
    original = path.read_text()
    for change in (
        original.replace("Addition", "Different contract"),
        original.replace("features/001-add/spec.md", "policy.md"),
        original + "\n```markdown\n<!-- finalize:spec-test:2026-10-17:1234abcd -->\n```\n",
    ):
        path.write_text(change)
        assert source_manifest(project, FEATURE) != before
    path.write_text(original)
