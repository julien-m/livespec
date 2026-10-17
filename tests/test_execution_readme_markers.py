"""Successive finalizations keep README bookkeeping outside execution identity."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from tests.execution_evidence_support import AC, FEATURE, run
from tests.execution_evidence_support import project as project
from tests.test_execution_finalize_scope import _registries
from validator.execution_evidence import verify_execution_receipt
from validator.execution_registry import registry_text
from validator.execution_scope import source_manifest
from validator.finalize import ApplyRequest, apply_finalization, verify_finalize_receipt


# @spec FR-011: Successive generated markers preserve the same execution inputs
# — .specs/features/078-requirement-evidence-integrity/spec.md#fr-011
def test_successive_real_implement_test_check_finalizations_preserve_execution(
    project: Path,
) -> None:
    _registries(project)
    before = source_manifest(project, FEATURE)
    receipt = run(project)
    for command in ("spec-implement", "spec-test", "spec-check"):
        result = apply_finalization(
            project,
            ApplyRequest(FEATURE, command, None, "Local verified", "Local verified", command),
            today=date(2026, 10, 17),
        )
        assert verify_finalize_receipt(result.receipt_path, project_root=project).verdict == "PASS"
        assert source_manifest(project, FEATURE) == before, command
        verified = verify_execution_receipt(receipt, project, FEATURE, (AC,))
        assert verified.valid, verified.gaps


def test_marker_lines_preserve_manual_boundaries_idempotence_and_fenced_examples() -> None:
    manual = "# Registry\n\nManual retention remains bounded.\n\nRead [policy](policy.md).\n"
    markers = "\n".join(
        f"<!-- finalize:spec-{command}:2026-10-17:{index:08x} -->\n"
        for index, command in enumerate(("implement", "test", "check"), 1)
    )
    after = manual + "\n" + markers
    projected = registry_text(".specs/README.md", after, FEATURE)
    assert projected == manual
    assert registry_text(".specs/README.md", projected, FEATURE) == projected
    changed = after.replace("remains bounded", "is unlimited")
    assert registry_text(".specs/README.md", changed, FEATURE) != projected
    fenced = manual + "\n```markdown\n" + markers + "```\n"
    assert registry_text(".specs/README.md", fenced, FEATURE) == fenced
    between = manual + "\n" + markers + "\nManual follow-up.\n"
    assert registry_text(".specs/README.md", between, FEATURE) == manual + "\nManual follow-up.\n"
