"""Generated history removal cannot join or erase adjacent manual Markdown."""

from __future__ import annotations

from pathlib import Path

from tests.execution_evidence_support import AC, FEATURE, run
from tests.execution_evidence_support import project as project
from tests.test_execution_finalize_scope import _finalize, _registries
from validator.execution_evidence import verify_execution_receipt
from validator.execution_registry import registry_text
from validator.execution_scope import source_manifest

MANUAL = (
    "## 2026-10-16 — Local operations checkpoint\n\n"
    "Read [the contract](policy.md). Retention remains bounded.\n"
)
GENERATED = (
    "## 2026-10-17 — Local release verified\n"
    "<!-- finalize:spec-implement:2026-10-17:1234abcd -->\n\n"
)


# @spec FR-011: Generated registry history retains manual input boundaries
# — .specs/features/078-requirement-evidence-integrity/spec.md#fr-011
def test_generated_entry_preserves_manual_heading_body_and_separator() -> None:
    before = "# Changelog\n\n" + MANUAL
    after = "# Changelog\n\n" + GENERATED + MANUAL
    assert registry_text(".specs/changelog.md", before, FEATURE) == before
    assert registry_text(".specs/changelog.md", after, FEATURE) == before


def test_actual_finalize_before_manual_entry_preserves_execution_receipt(project: Path) -> None:
    _registries(project)
    path = project / ".specs/changelog.md"
    path.write_text("# Changelog\n\n" + MANUAL)
    before = source_manifest(project, FEATURE)
    receipt = run(project)
    assert verify_execution_receipt(receipt, project, FEATURE, (AC,)).valid
    _finalize(project)  # Real registry writes and finalize receipt verification.
    assert path.read_text().endswith(MANUAL)
    assert source_manifest(project, FEATURE) == before
    verified = verify_execution_receipt(receipt, project, FEATURE, (AC,))
    assert verified.valid, verified.gaps


def test_generated_only_history_and_true_manual_edits_remain_distinct() -> None:
    original = "# Changelog\n\n" + GENERATED
    extended = "# Changelog\n\n" + GENERATED + GENERATED.replace("1234abcd", "5678abcd")
    assert registry_text(".specs/changelog.md", original, FEATURE) == registry_text(
        ".specs/changelog.md", extended, FEATURE
    )
    manual = "# Changelog\n\n" + GENERATED + MANUAL
    changed = manual.replace("Retention remains bounded.", "Retention is unlimited.")
    assert registry_text(".specs/changelog.md", manual, FEATURE) != registry_text(
        ".specs/changelog.md", changed, FEATURE
    )
    fenced = "# Changelog\n\n```markdown\n" + GENERATED + "```\n"
    assert "1234abcd" in registry_text(".specs/changelog.md", fenced, FEATURE)
