"""Structural validators for LiveSpec spec artifacts."""

import re
import yaml
from dataclasses import dataclass, field


@dataclass
class ValidationResult:
    valid: bool
    errors: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    count: int = 0
    story_count: int = 0
    orphan_frs: list[str] = field(default_factory=list)


def validate_frontmatter(content: str) -> ValidationResult:
    """Validate that YAML frontmatter is present and parseable."""
    match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
    if not match:
        return ValidationResult(valid=False, errors=["No YAML frontmatter found"])
    try:
        data = yaml.safe_load(match.group(1))
    except yaml.YAMLError as e:
        return ValidationResult(valid=False, errors=[f"Invalid YAML: {e}"])
    if not isinstance(data, dict):
        return ValidationResult(valid=False, errors=["Frontmatter is not an object"])
    return ValidationResult(valid=True)


def validate_spec_sections(content: str, required_sections: list[str]) -> ValidationResult:
    """Validate that all required sections are present in the content."""
    missing = [s for s in required_sections if s not in content]
    return ValidationResult(valid=len(missing) == 0, missing=missing)


def validate_gherkin_blocks(content: str, min_per_story: int = 2) -> ValidationResult:
    """Validate Gherkin blocks: presence, syntax, and count relative to stories."""
    blocks = re.findall(r'```gherkin\n(.*?)```', content, re.DOTALL)
    errors = []
    for i, block in enumerate(blocks):
        if "Feature:" not in block:
            errors.append(f"Block {i+1}: 'Feature:' missing")
        if "Scenario:" not in block:
            errors.append(f"Block {i+1}: 'Scenario:' missing")
    stories = re.findall(r'### Story \d+', content)
    story_count = len(stories)
    if blocks and story_count > 0 and len(blocks) < story_count * min_per_story:
        errors.append(
            f"Insufficient: {len(blocks)} Gherkin blocks for "
            f"{story_count} stories (min: {story_count * min_per_story})"
        )
    return ValidationResult(
        valid=len(errors) == 0,
        errors=errors,
        count=len(blocks),
        story_count=story_count,
    )


def validate_mermaid_blocks(content: str, expected_type: str = "flowchart") -> ValidationResult:
    """Validate Mermaid blocks of a given type and count them against stories."""
    pattern = rf'```mermaid\s*\n{re.escape(expected_type)}'
    matches = re.findall(pattern, content)
    stories = re.findall(r'### Story \d+', content)
    story_count = len(stories)
    count = len(matches)
    errors = []
    if story_count > 0 and count < story_count:
        errors.append(
            f"Insufficient: {count} {expected_type} diagrams for "
            f"{story_count} stories"
        )
    return ValidationResult(
        valid=len(errors) == 0,
        errors=errors,
        count=count,
        story_count=story_count,
    )


def validate_ac_fr_links(content: str) -> ValidationResult:
    """Validate that each FR references at least one AC in its neighborhood."""
    frs = re.findall(r'(FR-\d{3})', content)
    orphans = []
    for fr in set(frs):
        idx = content.find(fr)
        neighborhood = content[idx:idx + 500]
        if "AC-" not in neighborhood:
            orphans.append(fr)
    return ValidationResult(valid=len(orphans) == 0, orphan_frs=sorted(orphans))


def validate_spec_anchor_format(content: str) -> ValidationResult:
    """Validate that @spec anchors follow the format: @spec FR-NNN: description -- path#fragment."""
    anchor_pattern = re.compile(
        r'@spec\s+FR-\d{3}(?::\s+[^—]{1,50}\s+—\s+[^\s]+#fr-\d{3})?'
    )
    raw_anchors = re.findall(r'@spec\s+FR-\d{3}.*', content)
    errors = []
    for anchor in raw_anchors:
        if not anchor_pattern.match(anchor):
            errors.append(f"Malformed anchor: {anchor!r}")
    return ValidationResult(
        valid=len(errors) == 0,
        errors=errors,
        count=len(raw_anchors),
    )


def validate_roadmap_structure(content: str) -> ValidationResult:
    """Validate that the roadmap has all required HTML marker pairs."""
    required_pairs = [
        ("<!-- roadmap:mvp:start -->", "<!-- roadmap:mvp:end -->"),
        ("<!-- roadmap:postmvp:start -->", "<!-- roadmap:postmvp:end -->"),
        ("<!-- roadmap:future:start -->", "<!-- roadmap:future:end -->"),
        ("<!-- roadmap:deferred:start -->", "<!-- roadmap:deferred:end -->"),
    ]
    errors = []
    for start, end in required_pairs:
        if start not in content:
            errors.append(f"Missing marker: {start}")
        if end not in content:
            errors.append(f"Missing marker: {end}")
    # Check for at least one item in MVP
    mvp_match = re.search(
        r'<!-- roadmap:mvp:start -->(.*?)<!-- roadmap:mvp:end -->',
        content, re.DOTALL,
    )
    if mvp_match:
        items = re.findall(r'^- \[', mvp_match.group(1), re.MULTILINE)
        if len(items) == 0:
            errors.append("MVP section has no items")
    return ValidationResult(valid=len(errors) == 0, errors=errors)


def validate_readme_markers(content: str) -> ValidationResult:
    """Validate that README contains all required section markers."""
    required_markers = [
        "<!-- readme:features:start -->",
        "<!-- readme:features:end -->",
        "<!-- readme:decisions:start -->",
        "<!-- readme:decisions:end -->",
        "<!-- readme:activity:start -->",
        "<!-- readme:activity:end -->",
    ]
    missing = [m for m in required_markers if m not in content]
    return ValidationResult(
        valid=len(missing) == 0,
        missing=missing,
    )
