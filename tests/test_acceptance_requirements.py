"""Only declared obligations can change the kind of required acceptance evidence."""

from pathlib import Path

import pytest

from validator.acceptance_requirements import acceptance_inventory


def _inventory(root: Path, text: str):
    return acceptance_inventory(root, "001-test", spec_text=text)


def test_declared_table_and_heading_are_one_obligation_with_explicit_type(tmp_path: Path):
    text = (
        "# Feature\n## Acceptance Criteria\n| AC-001 | Runs |\n| AC-002 | Docs |\n"
        "### AC-002\n**Evidence:** review\n**Review inputs:** [source](inputs.json)\n"
        "## References\nAC-999: Not a declaration.\n### AC-998\nMention AC-997.\n"
    )
    items = _inventory(tmp_path, text)
    assert [item.requirement_id for item in items] == ["001-test:AC-001", "001-test:AC-002"]
    assert [item.evidence_kind for item in items] == ["execution", "review"]


@pytest.mark.parametrize("false_close", ["~~~", "```python", "``"])
def test_only_matching_empty_fence_can_close_examples(tmp_path: Path, false_close: str):
    items = _inventory(
        tmp_path,
        "# Feature\n```markdown\n" + false_close + "\n## AC-999\n```\n## AC-001\nReal criterion.\n",
    )
    assert [item.requirement_id for item in items] == ["001-test:AC-001"]


@pytest.mark.parametrize(
    "bad",
    [
        " **Evidence:** execution",
        "   **Evidence:** unknown",
        "  **Evidence :** execution",
        "**Evidence :** execution",
        "**Evidence:** unknown",
        "**Evidence:** execution",
        "**Review inputs :** [x](x.json)",
    ],
)
def test_malformed_or_conflicting_metadata_cannot_exempt_execution(tmp_path: Path, bad: str):
    text = (
        "# Feature\n## AC-001\n**Evidence:** review\n"
        "**Review inputs:** [source](inputs.json)\n" + bad
    )
    with pytest.raises(ValueError):
        _inventory(tmp_path, text)


def test_exact_supplied_bytes_and_legacy_root_declarations_are_used(tmp_path: Path):
    items = _inventory(
        tmp_path,
        "# Feature\nAC-001: One.\nAC-002: Two.\n"
        "## Examples\nAC-999: Example.\n<!--\n## AC-998\n-->\n",
    )
    assert [item.requirement_id for item in items] == ["001-test:AC-001", "001-test:AC-002"]
    assert all(item.evidence_kind == "execution" for item in items)


def test_missing_review_inputs_never_downgrades_to_documentary_prose(tmp_path: Path):
    with pytest.raises(ValueError, match="review_inputs"):
        _inventory(tmp_path, "# Feature\n## AC-001\n**Evidence:** review\n")
