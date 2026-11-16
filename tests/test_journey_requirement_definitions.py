"""Journey coverage accepts actual Markdown definitions, never incidental references."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from tests.test_journey_existing_tests import _reference_project
from validator.journeys.scanner import scan_journeys
from validator.journeys.validator import validate_journeys


@pytest.mark.parametrize(
    "definition",
    [
        "- **AC-001:** The original fixture exercises the criterion.",
        "## Acceptance Criteria\n\n| ID | Criterion | FR |\n|---|---|---|\n"
        "| AC-001 | The fixture must work. | FR-999 |",
        "## Acceptance criteria and requirements\n\n| ID | Criterion | FR |\n|---|---|---|\n"
        '| <a id="ac-001"></a>AC-001 | The fixture must work. | FR-999 |',
        "## Acceptance criteria\n\n### AC-001\n\nThe fixture must work.",
        '## Acceptance Criteria\n\n### <a id="ac-001"></a>AC-001 — Original fixture\n\n'
        "The fixture must work.",
        "## Acceptance criteria and requirements\n\n"
        '- <a id="ac-001"></a>**AC-001:** The fixture must work.',
    ],
)
def test_validate_and_doctor_recognize_maintained_definition_formats(
    tmp_path: Path, definition: str
) -> None:
    _reference_project(tmp_path)
    spec = tmp_path / ".specs/features/001-onboarding/spec.md"
    spec.write_text("# Original feature\n\n" + definition + "\n")
    result = validate_journeys(tmp_path)
    assert result.error_count == 0, result.issues
    assert len(result.journeys) == 1
    assert not [
        f for f in scan_journeys(tmp_path).findings if f.code == "journey_requirement_missing"
    ]


@pytest.mark.parametrize(
    "mention",
    [
        "The source refers to **AC-001:** for context only.",
        "## References\n\n- **AC-001:** See another document.",
        "## Examples\n\n### AC-001\n\nThis is an example, not a requirement.",
        "## Testing\n\n| AC | Test |\n|---|---|\n| AC-001 | checks/existing.py |",
        "## Traceability\n\n### AC-001\n\nMapped to an existing test, not declared here.",
        "## Acceptance Criteria\n\n### Implementation mapping\n\n"
        "| AC | Test |\n|---|---|\n| AC-001 | checks/existing.py |",
        "## Acceptance Criteria\n\n```markdown\n- **AC-001:** Code example.\n```",
        "## Acceptance Criteria\n\n> - **AC-001:** Quoted requirement.",
        "<!-- - **AC-001:** Hidden comment. -->",
        '---\nexample: "**AC-001:** Metadata only"\n---\n# Original feature',
        '## Acceptance Criteria\n\n<a id="ac-001"></a>',
        "## Acceptance Criteria\n\n- [AC-001](#elsewhere)",
        "## Acceptance Criteria\n\n| State | Reference |\n|---|---|\n| Ready | AC-001 |",
    ],
)
def test_incidental_mentions_cannot_satisfy_coverage(tmp_path: Path, mention: str) -> None:
    _reference_project(tmp_path)
    (tmp_path / ".specs/features/001-onboarding/spec.md").write_text(mention + "\n")
    result = validate_journeys(tmp_path)
    assert "journey_requirement_missing" in {issue.code for issue in result.issues}
    assert result.journeys == []


def test_functional_requirements_use_the_same_definition_discovery(tmp_path: Path) -> None:
    source = _reference_project(tmp_path)
    data = yaml.safe_load(source.read_text())
    data["covers"][0].update(kind="fr", ref="FR-003")
    source.write_text(yaml.safe_dump(data))
    (tmp_path / ".specs/features/001-onboarding/spec.md").write_text(
        "# Feature\n\n## Functional requirements\n\n"
        "| ID | Requirement | AC |\n|---|---|---|\n"
        '| <a id="fr-003"></a>FR-003 | The fixture must exercise the original test. | AC-001 |\n'
    )
    result = validate_journeys(tmp_path)
    assert result.error_count == 0, result.issues
    assert not [
        f for f in scan_journeys(tmp_path).findings if f.code == "journey_requirement_missing"
    ]


@pytest.mark.parametrize("separator", ["\n", "  \n"])
def test_consecutive_bold_definitions_keep_each_id_and_wrapped_body(separator: str) -> None:
    from validator.journeys.requirements import defined_requirement_ids

    text = "## Acceptance Criteria\n\n" + separator.join(
        [
            "**AC-001:** First required behavior.",
            "**AC-002:**",
            "A wrapped definition body.",
            "See **AC-998:** only an incidental reference.",
            "**AC-003:** Third required behavior.",
        ]
    )
    assert defined_requirement_ids(text) == {"AC-001", "AC-002", "AC-003"}


def test_combined_section_does_not_declare_reference_cells_or_anchor_names() -> None:
    from validator.journeys.requirements import defined_requirement_ids

    text = """## Acceptance criteria and requirements

| ID | Definition | References |
|---|---|---|
| <a id="ac-777"></a>AC-001 | The criterion must work. | FR-999 |

- **FR-003:** The system supports the criterion AC-001.
"""
    assert defined_requirement_ids(text) == {"AC-001", "FR-003"}
