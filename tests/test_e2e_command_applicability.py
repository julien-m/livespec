"""An explicit absent command is distinct from a pending or required E2E suite."""

from __future__ import annotations

import hashlib
from pathlib import Path

from validator.evidence_applicability import resolve_applicability
from validator.evidence_policy import apply_evidence_policy

FEATURE = "001-operations"
ROOT = Path(__file__).resolve().parents[1]
ABSENT = "| E2E cloud/visuel | Non exécutés | Cloud non autorisé ; visuel non applicable |\n"


def _project(root: Path, row: str = ABSENT) -> Path:
    directory = root / ".specs/features" / FEATURE
    directory.mkdir(parents=True)
    (directory / "spec.md").write_text("---\nvisual: false\n---\n# Operations\n")
    plan = directory / "plan.md"
    plan.write_text(
        "# Plan\n\n## Resolved Test Commands\n| Suite | Command | Scope |\n|---|---|---|\n" + row
    )
    return plan


# @spec FR-009: Only explicit absent command declarations remove an execution obligation
# — .specs/features/078-requirement-evidence-integrity/spec.md#fr-009
def test_absent_e2e_command_becomes_documentary_with_bound_plan_provenance(tmp_path: Path) -> None:
    plan = _project(tmp_path)
    result = resolve_applicability(tmp_path, FEATURE, "e2e-command")
    assert result["applicable"] is False, result
    assert result["reason"] == "explicit_no_command"
    assert result["source_sha256"] == hashlib.sha256(plan.read_bytes()).hexdigest()
    tasks = [
        {
            "id": "task.032.e2e",
            "description": "Run E2E tests with resolved E2E command (e.g. npx playwright test)",
            "required_evidence": ["observable_output_or_artifact", "success_criteria_met"],
        }
    ]
    apply_evidence_policy(
        tasks,
        ROOT / ".agent-sync/skills/spec-test/SKILL.md",
        project_root=tmp_path,
        feature=FEATURE,
    )
    assert tasks[0]["evidence_kind"] == "documentary"
    assert "execution_receipt_path" not in tasks[0]["required_evidence"]


def test_real_e2e_and_ambiguous_or_missing_declarations_stay_required(tmp_path: Path) -> None:
    plan = _project(tmp_path, "| E2E | `bun run test:e2e` | Local |\n")
    result = resolve_applicability(tmp_path, FEATURE, "e2e-command")
    assert result["applicable"] is True and result["reason"] == "declared"
    plan.write_text("# Plan\n## Resolved Test Commands\n| E2E | À déterminer | Local |\n")
    ambiguous = resolve_applicability(tmp_path, FEATURE, "e2e-command")
    assert ambiguous["applicable"] is True
    assert ambiguous["reason"] == "command_declaration_ambiguous"
    plan.write_text("# Plan\n")
    assert (
        resolve_applicability(tmp_path, FEATURE, "e2e-command")["reason"]
        == "test_discovery_required"
    )
    plan.unlink()
    assert (
        resolve_applicability(tmp_path, FEATURE, "e2e-command")["reason"] == "prerequisite_missing"
    )
    assert resolve_applicability(None, None, "e2e-command")["applicable"] is True


def test_visual_override_and_other_concrete_e2e_declarations_cannot_be_skipped(
    tmp_path: Path,
) -> None:
    plan = _project(tmp_path)
    plan.write_text(plan.read_text() + "| E2E local | `bun run test:e2e` | Required |\n")
    assert resolve_applicability(tmp_path, FEATURE, "e2e-command")["applicable"] is True
    plan.write_text("# Plan\n## Resolved Test Commands\n" + ABSENT)
    (plan.parent / "spec.md").write_text("---\nvisual: true\n---\n# Operations\n")
    result = resolve_applicability(tmp_path, FEATURE, "e2e-command")
    assert result["applicable"] is True and result["reason"] == "visual_execution_required"
