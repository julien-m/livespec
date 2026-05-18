"""Parser + override resolver for command expectations files.

# @spec FR-003: ExpectationsFile parser
#   — .specs/features/039-command-expectations-and-verify-output/spec.md#fr-003
# @spec FR-004: verify YAML grammar
#   — .specs/features/039-command-expectations-and-verify-output/spec.md#fr-004
# @spec FR-007: override lookup
#   — .specs/features/039-command-expectations-and-verify-output/spec.md#fr-007
# @spec FR-008: override total no merge
#   — .specs/features/039-command-expectations-and-verify-output/spec.md#fr-008
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

# PyYAML is a runtime dependency in this repo, but the local environment lacks
# typed stubs, so mypy needs an explicit boundary here.
import yaml  # type: ignore[import-untyped]

from .command_registry import short_command_name
from .exceptions import (
    ExpectationsInvalid,
    ExpectationsMissing,
    OverrideMalformed,
)

# Required prose section headings, in order.
REQUIRED_SECTIONS: tuple[str, ...] = (
    "1. Purpose",
    "2. Preconditions",
    "3. Observable Signals",
    "4. Filesystem Effects",
    "5. Git Effects",
    "6. Produced Artifacts",
    "7. Exit Codes",
    "8. Outcome Matrix",
    "9. Runtime Profile",
    "10. Post-run Checks",
    "11. Troubleshooting",
    "12. Verify Contract",
    "13. Demo Session",
)

# Required Section 13 sub-sections, in canonical order.
# Each sub-section is identified by an h3 heading whose text contains the
# canonical slug (case-insensitive substring match, leading "13.N " allowed).
SECTION13_SUBSECTIONS: tuple[str, ...] = (
    "Live Console Output",
    "Files Produced",
    "Aligned / Drift / Missing",
    "Runtime Profile",
    "Edge Cases",
    "Post-run Actions",
)

# Minimum number of non-empty content lines per Section 13 sub-section.
SECTION13_MIN_CONTENT_LINES: int = 3

RULE_KINDS: frozenset[str] = frozenset(
    {"contains", "exists", "exit_code", "produces_artifact"}
)


@dataclass(frozen=True)
class Rule:
    """A single assertion inside a verify block."""

    verb: str  # "must" | "may" | "must_not"
    kind: str  # "contains" | "exists" | "exit_code" | "produces_artifact"
    payload: Any  # str | int | dict (for produces_artifact)


def _empty_rule_list() -> list[Rule]:
    """Typed default factory for ``list[Rule]`` dataclass fields."""
    return []


def _empty_when_list() -> list[WhenBranch]:
    """Typed default factory for ``list[WhenBranch]`` dataclass fields."""
    return []


@dataclass(frozen=True)
class WhenBranch:
    """Conditional rule set activated by a flag."""

    flag: str
    must: list[Rule] = field(default_factory=_empty_rule_list)
    may: list[Rule] = field(default_factory=_empty_rule_list)
    must_not: list[Rule] = field(default_factory=_empty_rule_list)


@dataclass(frozen=True)
class VerifyBlock:
    """Parsed `verify:` YAML block from section 12."""

    must: list[Rule] = field(default_factory=_empty_rule_list)
    may: list[Rule] = field(default_factory=_empty_rule_list)
    must_not: list[Rule] = field(default_factory=_empty_rule_list)
    when: list[WhenBranch] = field(default_factory=_empty_when_list)


@dataclass(frozen=True)
class DemoSession:
    """Parsed Section 13 (Demo Session) — six required sub-sections.

    @spec FR-003: Section 13 parser
        .specs/features/040-expectations-rich-and-verify-preview/spec.md#fr-003
    """

    live_console_output: str
    files_produced: str
    aligned_drift_missing: str
    runtime_profile: str
    edge_cases: str
    post_run_actions: str

    def as_mapping(self) -> dict[str, str]:
        """Return the sub-sections keyed by canonical sub-heading name."""
        return {
            "Live Console Output": self.live_console_output,
            "Files Produced": self.files_produced,
            "Aligned / Drift / Missing": self.aligned_drift_missing,
            "Runtime Profile": self.runtime_profile,
            "Edge Cases": self.edge_cases,
            "Post-run Actions": self.post_run_actions,
        }


@dataclass(frozen=True)
class ExpectationsFile:
    """Parsed expectations.md file."""

    command: str
    contract_version: str
    last_reviewed: str
    prose_sections: dict[str, str]
    verify: VerifyBlock
    source_path: Path
    demo_session: DemoSession | None = None


def parse_expectations(path: Path) -> ExpectationsFile:
    """Parse a command-expectations Markdown file.

    Args:
        path: Path to the expectations file.

    Returns:
        Parsed :class:`ExpectationsFile`.

    Raises:
        ExpectationsInvalid: when the file fails schema validation.
        FileNotFoundError: when the path does not exist.
    """
    text = path.read_text(encoding="utf-8")
    frontmatter, body = _split_frontmatter(path, text)
    _validate_frontmatter(path, frontmatter)
    sections = _extract_sections(path, body)
    verify = _extract_verify_block(path, sections["12. Verify Contract"])
    demo_session = _extract_demo_session(path, sections["13. Demo Session"])
    return ExpectationsFile(
        command=str(frontmatter["command"]),
        contract_version=str(frontmatter["contract_version"]),
        last_reviewed=str(frontmatter["last_reviewed"]),
        prose_sections=sections,
        verify=verify,
        source_path=path,
        demo_session=demo_session,
    )


def load_expectations(
    command: str,
    project_root: Path,
    livespec_root: Path,
) -> ExpectationsFile:
    """Resolve and parse the expectations file for a command.

    Lookup order (first match wins, total — no merge):
      1. ``<project_root>/.specs/expectations/<command>.md``
      2. ``<livespec_root>/commands/<command>.expectations.md``

    A malformed project override raises :class:`OverrideMalformed`. The
    verifier MUST NOT silently fall back to the builtin (AC-007).

    Args:
        command: The command name.
        project_root: Root of the user project (parent of ``.specs``).
        livespec_root: Root of the LiveSpec checkout (parent of ``commands``).

    Returns:
        Parsed :class:`ExpectationsFile`.

    Raises:
        OverrideMalformed: when the project override is malformed.
        ExpectationsMissing: when neither path exists.
        ExpectationsInvalid: when the builtin is malformed.
    """
    legacy_command = short_command_name(command)
    override = project_root / ".specs" / "expectations" / f"{command}.md"
    legacy_override = project_root / ".specs" / "expectations" / f"{legacy_command}.md"
    builtin = livespec_root / "commands" / f"{command}.expectations.md"
    searched = [str(override)]
    if legacy_override != override:
        searched.append(str(legacy_override))
    searched.append(str(builtin))

    if override.exists():
        try:
            return parse_expectations(override)
        except ExpectationsInvalid as exc:
            raise OverrideMalformed(str(override), exc.reason) from exc

    if legacy_override != override and legacy_override.exists():
        try:
            return parse_expectations(legacy_override)
        except ExpectationsInvalid as exc:
            raise OverrideMalformed(str(legacy_override), exc.reason) from exc

    if builtin.exists():
        return parse_expectations(builtin)

    raise ExpectationsMissing(command, searched)


# ---------- helpers ----------


def _split_frontmatter(path: Path, text: str) -> tuple[dict[str, Any], str]:
    """Split YAML frontmatter from the body."""
    if not text.startswith("---"):
        raise ExpectationsInvalid(str(path), "missing YAML frontmatter")
    # Robust split: find the second '---' on its own line.
    lines = text.splitlines()
    if lines[0].strip() != "---":
        raise ExpectationsInvalid(str(path), "frontmatter must start at line 1")
    end_idx = -1
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end_idx = i
            break
    if end_idx == -1:
        raise ExpectationsInvalid(str(path), "frontmatter is not closed")
    fm_text = "\n".join(lines[1:end_idx])
    body = "\n".join(lines[end_idx + 1 :])
    try:
        raw: Any = yaml.safe_load(fm_text) or {}
    except yaml.YAMLError as exc:
        raise ExpectationsInvalid(str(path), f"frontmatter YAML error: {exc}") from exc
    if not isinstance(raw, dict):
        raise ExpectationsInvalid(str(path), "frontmatter must be a mapping")
    raw_dict = cast(dict[Any, Any], raw)
    data: dict[str, Any] = {str(k): v for k, v in raw_dict.items()}
    return data, body


def _validate_frontmatter(path: Path, fm: dict[str, Any]) -> None:
    """Ensure required frontmatter keys are present and well-formed."""
    for key in ("command", "contract_version", "last_reviewed"):
        if key not in fm:
            raise ExpectationsInvalid(str(path), f"frontmatter missing '{key}'")
    lr = str(fm["last_reviewed"])
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", lr):
        raise ExpectationsInvalid(
            str(path),
            f"last_reviewed must be YYYY-MM-DD (got {lr!r})",
        )


_HEADING_RE = re.compile(r"^##\s+(\d+\.\s+[^\n]+?)\s*$", re.MULTILINE)


def _extract_sections(path: Path, body: str) -> dict[str, str]:
    """Extract the 12 required sections by exact heading text."""
    matches = list(_HEADING_RE.finditer(body))
    if not matches:
        raise ExpectationsInvalid(str(path), "no '## N. ...' headings found")

    found_titles = [m.group(1).strip() for m in matches]
    missing = [s for s in REQUIRED_SECTIONS if s not in found_titles]
    if missing:
        # AC-008 mandates a precise message when Section 13 is the missing one.
        # @spec AC-008: section 13 missing message —
        #   .specs/features/040-expectations-rich-and-verify-preview/spec.md#ac-008
        if missing == ["13. Demo Session"] or (
            "13. Demo Session" in missing and len(missing) == 1
        ):
            raise ExpectationsInvalid(
                str(path),
                f"section 13 missing in {path.as_posix()}",
            )
        raise ExpectationsInvalid(
            str(path),
            f"missing required section(s): {', '.join(missing)}",
        )

    sections: dict[str, str] = {}
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        title = m.group(1).strip()
        sections[title] = body[start:end].strip()
    return sections


_YAML_FENCE_RE = re.compile(
    r"```yaml\s*\n(.*?)\n```",
    re.DOTALL,
)


def _extract_verify_block(path: Path, section_body: str) -> VerifyBlock:
    """Pull the fenced ```yaml verify: ...``` block from section 12."""
    match = _YAML_FENCE_RE.search(section_body)
    if not match:
        raise ExpectationsInvalid(
            str(path),
            "section '12. Verify Contract' missing ```yaml ...``` block",
        )
    try:
        raw: Any = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError as exc:
        raise ExpectationsInvalid(
            str(path),
            f"verify YAML parse error: {exc}",
        ) from exc
    if not isinstance(raw, dict) or "verify" not in raw:
        raise ExpectationsInvalid(
            str(path),
            "verify block must have a top-level 'verify:' key",
        )
    raw_typed = cast(dict[Any, Any], raw)
    verify_data: Any = raw_typed["verify"]
    if not isinstance(verify_data, dict):
        raise ExpectationsInvalid(str(path), "verify: must be a mapping")
    verify_typed = cast(dict[Any, Any], verify_data)
    verify_dict: dict[str, Any] = {str(k): v for k, v in verify_typed.items()}
    return _build_verify_block(path, verify_dict)


def _build_verify_block(path: Path, data: dict[str, Any]) -> VerifyBlock:
    """Construct a :class:`VerifyBlock` from a parsed YAML mapping."""
    must = _parse_rule_list(path, data.get("must"), "must")
    may = _parse_rule_list(path, data.get("may"), "may")
    must_not = _parse_rule_list(path, data.get("must_not"), "must_not")
    when_raw_any: Any = data.get("when") or []
    if not isinstance(when_raw_any, list):
        raise ExpectationsInvalid(str(path), "verify.when must be a list")
    when_raw = cast(list[Any], when_raw_any)
    when: list[WhenBranch] = []
    for raw_entry in when_raw:
        if not isinstance(raw_entry, dict) or "flag" not in raw_entry:
            raise ExpectationsInvalid(
                str(path),
                "each when: entry must be a mapping with a 'flag' key",
            )
        raw_entry_typed = cast(dict[Any, Any], raw_entry)
        entry: dict[str, Any] = {str(k): v for k, v in raw_entry_typed.items()}
        when.append(
            WhenBranch(
                flag=str(entry["flag"]),
                must=_parse_rule_list(path, entry.get("must"), "must"),
                may=_parse_rule_list(path, entry.get("may"), "may"),
                must_not=_parse_rule_list(path, entry.get("must_not"), "must_not"),
            )
        )
    return VerifyBlock(must=must, may=may, must_not=must_not, when=when)


def _parse_rule_list(
    path: Path,
    raw: Any,
    verb: str,
) -> list[Rule]:
    """Convert a raw rule list (YAML) into typed :class:`Rule` objects."""
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise ExpectationsInvalid(str(path), f"verify.{verb} must be a list")
    raw_list = cast(list[Any], raw)
    rules: list[Rule] = []
    for item_any in raw_list:
        if not isinstance(item_any, dict):
            raise ExpectationsInvalid(
                str(path),
                f"verify.{verb} entry must be a mapping (got {type(item_any).__name__})",
            )
        item_typed = cast(dict[Any, Any], item_any)
        item: dict[str, Any] = {str(k): v for k, v in item_typed.items()}
        kind, payload = _resolve_rule_kind(path, item, verb)
        rules.append(Rule(verb=verb, kind=kind, payload=payload))
    return rules


def _resolve_rule_kind(
    path: Path,
    item: dict[str, Any],
    verb: str,
) -> tuple[str, Any]:
    """Determine the Rule kind from the mapping keys."""
    keys = set(item.keys())
    if "produces_artifact" in keys:
        sections_raw: Any = item.get("contains_sections") or []
        sections_list = cast(list[Any], sections_raw) if isinstance(sections_raw, list) else []
        return "produces_artifact", {
            "path": str(item["produces_artifact"]),
            "contains_sections": [str(s) for s in sections_list],
        }
    for kind in ("contains", "exists", "exit_code"):
        if kind in keys:
            return kind, item[kind]
    raise ExpectationsInvalid(
        str(path),
        f"verify.{verb} entry uses unknown rule kind: {sorted(keys)}",
    )


# ---------- Section 13 (Demo Session) parser ----------

# Tolerant h3 heading regex: matches "### Foo", "### 13.1 Foo", "### 13.1. Foo".
_H3_RE = re.compile(r"^###\s+(?:13\.\d+\.?\s+)?(.+?)\s*$", re.MULTILINE)


def _normalize_subheading(text: str) -> str:
    """Normalize a sub-heading for fuzzy matching against canonical names."""
    return re.sub(r"[^a-z0-9 ]", "", text.strip().lower())


def _match_subsection_slot(heading: str) -> str | None:
    """Map a raw h3 heading to one of the 6 canonical Section 13 sub-section slots."""
    normalized = _normalize_subheading(heading)
    for canonical in SECTION13_SUBSECTIONS:
        canonical_norm = _normalize_subheading(canonical)
        if canonical_norm in normalized or normalized in canonical_norm:
            return canonical
    # Looser fallback: match on first significant word.
    first_word = normalized.split(" ", 1)[0]
    aliases = {
        "live": "Live Console Output",
        "console": "Live Console Output",
        "files": "Files Produced",
        "produced": "Files Produced",
        "aligned": "Aligned / Drift / Missing",
        "drift": "Aligned / Drift / Missing",
        "missing": "Aligned / Drift / Missing",
        "runtime": "Runtime Profile",
        "scenarios": "Runtime Profile",
        "edge": "Edge Cases",
        "post": "Post-run Actions",
        "postrun": "Post-run Actions",
    }
    return aliases.get(first_word)


def _content_line_count(body: str) -> int:
    """Count non-empty, non-comment, non-fence content lines."""
    count = 0
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("<!--") and stripped.endswith("-->"):
            continue
        if stripped == "```" or stripped.startswith("```"):
            # Fence lines count as content (they prove an example block exists).
            count += 1
            continue
        count += 1
    return count


def _extract_demo_session(path: Path, section_body: str) -> DemoSession:
    """Parse Section 13 into the six required sub-sections.

    @spec FR-003: Section 13 enforcement
        .specs/features/040-expectations-rich-and-verify-preview/spec.md#fr-003
    @spec AC-008: missing-section message
        .specs/features/040-expectations-rich-and-verify-preview/spec.md#ac-008
    @spec AC-009: empty-sub-section message
        .specs/features/040-expectations-rich-and-verify-preview/spec.md#ac-009
    """
    matches = list(_H3_RE.finditer(section_body))
    if not matches:
        raise ExpectationsInvalid(
            str(path),
            "section 13 sub-section 'Live Console Output' is empty",
        )

    slots: dict[str, str] = {}
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(section_body)
        slot = _match_subsection_slot(m.group(1))
        if slot is None:
            continue
        body = section_body[start:end].strip()
        slots[slot] = body

    for canonical in SECTION13_SUBSECTIONS:
        if canonical not in slots:
            raise ExpectationsInvalid(
                str(path),
                f"section 13 sub-section '{canonical}' is empty",
            )
        if _content_line_count(slots[canonical]) < SECTION13_MIN_CONTENT_LINES:
            raise ExpectationsInvalid(
                str(path),
                f"section 13 sub-section '{canonical}' is empty",
            )

    return DemoSession(
        live_console_output=slots["Live Console Output"],
        files_produced=slots["Files Produced"],
        aligned_drift_missing=slots["Aligned / Drift / Missing"],
        runtime_profile=slots["Runtime Profile"],
        edge_cases=slots["Edge Cases"],
        post_run_actions=slots["Post-run Actions"],
    )


__all__ = [
    "REQUIRED_SECTIONS",
    "RULE_KINDS",
    "SECTION13_MIN_CONTENT_LINES",
    "SECTION13_SUBSECTIONS",
    "DemoSession",
    "ExpectationsFile",
    "Rule",
    "VerifyBlock",
    "WhenBranch",
    "load_expectations",
    "parse_expectations",
]
