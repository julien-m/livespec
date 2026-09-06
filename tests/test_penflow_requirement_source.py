"""Feature 077 definitions and semantic identity retain source authority."""

from pathlib import Path

import pytest

from validator.penflow_requirement_source import (
    RequirementSourceError,
    extract_requirement_definitions,
    semantic_source_sha256,
)

SOURCE = """---
title: Checkout
status: Approved
updated: 2026-09-05
visual: true
---
# Checkout
- **Status:** Approved
## Functional Requirements
- **FR-001:** Save the order (AC-001).
## Acceptance Criteria
- **AC-001:** The saved order appears after refresh.
"""


def _source(tmp_path: Path, text: str = SOURCE) -> Path:
    path = tmp_path / "spec.md"
    path.write_text(text)
    return path


# @spec AC-008: derive source definitions without interpreting narrative mentions
# — .specs/features/077-penflow-cumulative-verdict-consumer/spec.md#ac-008
def test_extracts_namespaced_definitions_and_references(tmp_path: Path) -> None:
    definitions = extract_requirement_definitions(_source(tmp_path), "001-checkout")
    assert [item.id for item in definitions] == [
        "livespec:001-checkout:FR-001",
        "livespec:001-checkout:AC-001",
    ]
    assert definitions[0].references == ("livespec:001-checkout:AC-001",)
    assert definitions[0].text == "Save the order (AC-001)."
    assert definitions[0].source_pointer.startswith("/body/")
    assert len(definitions[0].text_sha256) == 64


def test_table_definitions_and_mentions_outside_scope(tmp_path: Path) -> None:
    text = """# Spec
See FR-099 and AC-999.
## Functional Requirements
| ID | Requirement | AC References |
|---|---|---|
| FR-001 | Save order | AC-001 |
```markdown
- FR-888: Example only (AC-888).
```
## Acceptance Criteria
| ID | Criterion |
|---|---|
| AC-001 | Saved order is visible |
"""
    items = extract_requirement_definitions(_source(tmp_path, text), "001-checkout")
    assert [item.local_id for item in items] == ["FR-001", "AC-001"]
    assert items[0].references == ("livespec:001-checkout:AC-001",)


def test_extracts_canonical_split_feature_namespace(tmp_path: Path) -> None:
    definitions = extract_requirement_definitions(_source(tmp_path), "005.1-feature")
    assert [item.id for item in definitions] == [
        "livespec:005.1-feature:FR-001",
        "livespec:005.1-feature:AC-001",
    ]
    assert definitions[0].references == ("livespec:005.1-feature:AC-001",)


@pytest.mark.parametrize(
    "definition",
    [
        "FR-002: Restore after restart (AC-001).",
        "**FR-002:** Restore after restart (AC-001).",
        "FR-BOGUS: Restore after restart (AC-001).",
        "### FR-002: Restore after restart (AC-001).",
        "## FR-BOGUS: Restore after restart (AC-001).",
        "AC-002: Restore after restart.",
    ],
)
def test_rejects_unsupported_definition_in_authoritative_section(
    tmp_path: Path, definition: str
) -> None:
    text = SOURCE.replace("## Acceptance Criteria", f"\n{definition}\n\n## Acceptance Criteria")
    with pytest.raises(
        RequirementSourceError, match=r"unsupported_requirement_definition: /body/\d+"
    ):
        extract_requirement_definitions(_source(tmp_path, text), "001-checkout")


@pytest.mark.parametrize(
    "example",
    [
        "See FR-002: this is a cross-reference.",
        "Introductory prose without a definition.",
        "```markdown\nFR-002: Example only (AC-999).\n```",
        "> FR-002: Example only (AC-999).",
        "<div>FR-002: Example only (AC-999).</div>",
    ],
)
def test_ignores_mentions_and_examples_in_authoritative_section(
    tmp_path: Path, example: str
) -> None:
    text = SOURCE.replace("## Acceptance Criteria", f"\n{example}\n\n## Acceptance Criteria")
    definitions = extract_requirement_definitions(_source(tmp_path, text), "001-checkout")
    assert [item.local_id for item in definitions] == ["FR-001", "AC-001"]


def test_ignores_definition_shaped_paragraph_outside_requirement_sections(tmp_path: Path) -> None:
    text = SOURCE + "\n## Notes\n\nFR-002: Example only (AC-999).\n"
    definitions = extract_requirement_definitions(_source(tmp_path, text), "001-checkout")
    assert [item.local_id for item in definitions] == ["FR-001", "AC-001"]


@pytest.mark.parametrize("separator", ["\n", "  \n"])
def test_rejects_definition_after_paragraph_linebreak(tmp_path: Path, separator: str) -> None:
    text = SOURCE.replace(
        "## Acceptance Criteria",
        f"\nIntroduction.{separator}FR-002: Restore (AC-001).\n\n## Acceptance Criteria",
    )
    with pytest.raises(RequirementSourceError, match="unsupported_requirement_definition"):
        extract_requirement_definitions(_source(tmp_path, text), "001-checkout")


@pytest.mark.parametrize(
    "text",
    [
        SOURCE + "\n- **AC-001:** Duplicate definition.\n",
        SOURCE.replace("Save the order (AC-001).", ""),
        SOURCE.replace("(AC-001)", "(AC-999)"),
        SOURCE.replace("- **AC-001:** The saved order appears after refresh.", ""),
        SOURCE.replace("FR-001", "FR-BOGUS"),
        "# Spec\nOnly a mention of FR-001 and AC-001.\n",
    ],
)
def test_rejects_incomplete_ambiguous_or_malformed_sources(tmp_path: Path, text: str) -> None:
    with pytest.raises(RequirementSourceError):
        extract_requirement_definitions(_source(tmp_path, text), "001-checkout")


def test_semantic_identity_ignores_only_lifecycle_metadata(tmp_path: Path) -> None:
    path = _source(tmp_path)
    expected = semantic_source_sha256(path)
    path.write_text(
        SOURCE.replace("Approved", "Implemented").replace("2026-09-05", "2026-09-06")
        + "\n<!-- finalize:spec-implement:2026-09-06:abcdef12 -->\n"
    )
    assert semantic_source_sha256(path) == expected


@pytest.mark.parametrize(
    "changed",
    [
        SOURCE.replace("visual: true", "visual: false"),
        SOURCE.replace("Save the order", "Cancel the order"),
        SOURCE.replace("after refresh", "before refresh"),
        SOURCE + "\n## Business\n\n- **Status:** Approved\n",
        SOURCE + "\n```text\n- **Status:** Approved\nupdated: 2026-09-05\n```\n",
        SOURCE + "\n<!-- business policy: preserve draft -->\n",
        SOURCE + "\n<!-- finalize:spec-implement:2026-09-06:not-a-hash -->\n",
    ],
)
def test_semantic_identity_retains_business_and_code_content(tmp_path: Path, changed: str) -> None:
    path = _source(tmp_path)
    expected = semantic_source_sha256(path)
    path.write_text(changed)
    assert semantic_source_sha256(path) != expected


@pytest.mark.parametrize(
    "body",
    [
        "\n## Business\n\n- **Status:** Approved\n",
        "\n```text\n- **Status:** Approved\nupdated: 2026-09-05\n```\n",
    ],
)
def test_lifecycle_exclusion_does_not_remove_business_status_updates(
    tmp_path: Path, body: str
) -> None:
    path = _source(tmp_path, SOURCE + body)
    expected = semantic_source_sha256(path)
    path.write_text((SOURCE + body).replace("Approved", "Implemented"))
    assert semantic_source_sha256(path) != expected


def test_real_finalization_preserves_semantic_source_identity(tmp_path: Path) -> None:
    from tests.test_finalize import _implement_request, _make_specs_tree
    from validator.finalize import apply_finalization, verify_finalization

    specs = _make_specs_tree(tmp_path)
    request = _implement_request()
    path = specs / "features" / request.feature_slug / "spec.md"
    path.write_text(
        SOURCE.replace("title: Checkout", "title: Notifications").replace(
            "visual: true", "visual: false"
        )
    )
    expected = semantic_source_sha256(path)
    apply_finalization(tmp_path, request)
    assert (
        verify_finalization(tmp_path, request.feature_slug, run_id="semantic-check").verdict
        == "PASS"
    )
    assert semantic_source_sha256(path) == expected
