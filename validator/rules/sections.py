"""Section presence validation rules for each file type."""

from __future__ import annotations

# Immutable by convention — do not mutate at runtime
SECTION_RULES: dict[str, dict[str, tuple[list[str], bool]]] = {
    "spec": {
        "stories": (["User Scenarios", "User Stories", "Scenarios"], True),
        "ac": (["Acceptance Criteria"], True),
        "fr": (["Functional Requirements"], True),
        "edge": (["Edge Cases"], True),
    },
    "plan": {
        "summary": (["Summary"], True),
        "impl": (["Implementation Plan", "Implementation Steps"], True),
        "testing": (["Testing Strategy", "Test"], True),
        "risks": (["Risks", "Considerations"], True),
    },
    "implementation": {
        "req_mapping": (["Requirement Mapping", "FR Mapping"], True),
        "ac_mapping": (["Acceptance Criteria", "AC Coverage"], True),
    },
    "stack": {
        "stack": (["Stack", "Choices", "Overview"], True),
        "rationale": (["Rationale", "Decisions", "Why"], True),
    },
    "preflight": {
        "tooling": (["Tooling"], True),
        "auth": (["Authentication", "Auth"], True),
        "tokens": (["Tokens", "Credentials", "Keys"], True),
    },
}


def section_present(headings: list[str], keywords: list[str]) -> bool:
    """Return True if any keyword appears in any heading (case-insensitive).

    Args:
        headings: List of heading texts extracted from the markdown.
        keywords: Keyword patterns to search for.

    Returns:
        True if at least one keyword matches a heading.
    """
    lower_headings = [h.lower() for h in headings]
    return any(
        kw.lower() in heading
        for heading in lower_headings
        for kw in keywords
    )


def validate_sections(
    headings: list[str], file_type: str
) -> tuple[list[str], list[str]]:
    """Validate section presence for a given file type.

    Args:
        headings: Heading texts from the parsed markdown.
        file_type: Spec file type to look up in SECTION_RULES.

    Returns:
        Tuple of (errors, warnings) — each a list of message strings.
    """
    errors: list[str] = []
    warnings: list[str] = []

    rules = SECTION_RULES.get(file_type, {})
    for key, (keywords, required) in rules.items():
        if not section_present(headings, keywords):
            msg = f"Missing section '{key}' (expected one of: {', '.join(keywords)})"
            if required:
                errors.append(msg)
            else:
                warnings.append(msg)

    return errors, warnings
