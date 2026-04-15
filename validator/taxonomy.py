"""Parse ui-behavioral-taxonomy.md and expose detect_traits / deduplicate_tests.

@spec FR-001 — load_taxonomy — .specs/features/006-taxonomy-testing-infra/spec.md#fr-001
@spec FR-002 — path resolution — .specs/features/006-taxonomy-testing-infra/spec.md#fr-002
@spec FR-003 — detect_traits — .specs/features/006-taxonomy-testing-infra/spec.md#fr-003
@spec FR-004 — co-occurrence — .specs/features/006-taxonomy-testing-infra/spec.md#fr-004
@spec FR-005 — deduplicate_tests — .specs/features/006-taxonomy-testing-infra/spec.md#fr-005
@spec FR-006 — EC-004 dedup — .specs/features/006-taxonomy-testing-infra/spec.md#fr-006
@spec FR-007 — TaxonomyLoadError — .specs/features/006-taxonomy-testing-infra/spec.md#fr-007
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import mistune

from validator.exceptions import TaxonomyLoadError

logger = logging.getLogger(__name__)

# Default path: two levels up from this file → repo root / system/testing/...
_TAXONOMY_PATH: Path = (
    Path(__file__).parent.parent / "system" / "testing" / "ui-behavioral-taxonomy.md"
)

# Module-level cache keyed by resolved path (supports test isolation via different paths)
_TAXONOMY_CACHE: dict[Path, Taxonomy] = {}


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class TestPattern:
    """A named test pattern extracted from the taxonomy."""

    name: str
    keyword: str
    description: str


@dataclass
class DetectionSignal:
    """One detection signal entry for a trait."""

    text: str
    unambiguous: bool  # True → fires alone; False → requires ≥2 UI signals


@dataclass
class Trait:
    """A single behavioral trait parsed from the taxonomy."""

    name: str
    description: str
    detection_signals: list[DetectionSignal] = field(default_factory=lambda: [])
    gherkin_template: str = ""
    test_patterns: list[TestPattern] = field(default_factory=lambda: [])


@dataclass
class TransversalPattern:
    """A named combination of constituent traits."""

    name: str
    constituent_traits: list[str] = field(default_factory=lambda: [])
    disambiguation: str = ""
    combined_gherkin_template: str = ""


@dataclass
class Taxonomy:
    """Parsed taxonomy document."""

    traits: list[Trait] = field(default_factory=lambda: [])
    transversal_patterns: list[TransversalPattern] = field(default_factory=lambda: [])

    def trait_by_name(self, name: str) -> Trait | None:
        """Return the Trait with the given name, or None."""
        for t in self.traits:
            if t.name == name:
                return t
        return None


@dataclass
class MergedTest:
    """Result of deduplication — one logical test referencing AC and/or trait."""

    ref: str
    behavioral_trait: str | None
    ac_id: str | None
    gherkin: str


# ---------------------------------------------------------------------------
# Markdown parsing helpers
# ---------------------------------------------------------------------------

_UNAMBIGUOUS_MARKERS = (
    "sufficient alone",
    "unambiguous",
)


def _node_text(node: dict[str, Any]) -> str:
    """Recursively extract plain text from a mistune AST node."""
    if node.get("type") == "text":
        return str(node.get("raw", ""))
    parts: list[str] = []
    children: list[dict[str, Any]] = node.get("children") or []
    for child in children:
        parts.append(_node_text(child))
    return "".join(parts)


def _ast_nodes_text(nodes: list[dict[str, Any]]) -> str:
    return "".join(_node_text(n) for n in nodes)


def _is_unambiguous(context_text: str) -> bool:
    lower = context_text.lower()
    return any(m in lower for m in _UNAMBIGUOUS_MARKERS)


def _table_parts(
    table_node: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return (head_cells, body_rows) for a mistune 3 table node.

    Mistune 3 structure: table → [table_head, table_body]
      table_head.children = [table_cell, ...]
      table_body.children = [table_row, ...]
      table_row.children  = [table_cell, ...]
    """
    head_cells: list[dict[str, Any]] = []
    body_rows: list[dict[str, Any]] = []
    for child in table_node.get("children", []):
        child_type = child.get("type", "")
        if child_type == "table_head":
            head_cells = child.get("children", [])
        elif child_type == "table_body":
            body_rows = child.get("children", [])
    return head_cells, body_rows


def _parse_detection_signals(
    nodes: list[dict[str, Any]],
) -> list[DetectionSignal]:
    """Extract detection signals from the table that follows '**Detection signals:**'."""
    signals: list[DetectionSignal] = []
    in_table = False
    for node in nodes:
        if node.get("type") == "table":
            in_table = True
            head_cells, body_rows = _table_parts(node)
            if not head_cells:
                continue
            # Identify column indices for Signal and Context requirement
            headers = [_node_text(c).strip().lower() for c in head_cells]
            try:
                sig_idx = headers.index("signal")
                ctx_idx = headers.index("context requirement")
            except ValueError:
                continue
            for row_node in body_rows:
                cells = row_node.get("children", [])
                if len(cells) <= max(sig_idx, ctx_idx):
                    continue
                raw_signal = _node_text(cells[sig_idx]).strip().strip('"')
                raw_context = _node_text(cells[ctx_idx]).strip()
                if not raw_signal:
                    continue
                unambiguous = _is_unambiguous(raw_context)
                signals.append(DetectionSignal(text=raw_signal.lower(), unambiguous=unambiguous))
        else:
            if in_table:
                break
    return signals


def _parse_test_patterns(nodes: list[dict[str, Any]]) -> list[TestPattern]:
    """Extract test patterns from the table that follows '**Test patterns:**'."""
    patterns: list[TestPattern] = []
    for node in nodes:
        if node.get("type") != "table":
            continue
        head_cells, body_rows = _table_parts(node)
        if not head_cells:
            continue
        headers: list[str] = [_node_text(c).strip().lower() for c in head_cells]
        # Normalise "pattern keyword" → "keyword", "pattern name" → "name"
        norm: list[str] = []
        for h in headers:
            if "keyword" in h:
                norm.append("keyword")
            elif "name" in h:
                norm.append("name")
            elif "description" in h:
                norm.append("description")
            else:
                norm.append(h)
        try:
            name_idx = norm.index("name")
            kw_idx = norm.index("keyword")
            desc_idx = norm.index("description")
        except ValueError:
            continue
        for row_node in body_rows:
            cells = row_node.get("children", [])
            if len(cells) <= max(name_idx, kw_idx, desc_idx):
                continue
            p_name = _node_text(cells[name_idx]).strip()
            p_kw = _node_text(cells[kw_idx]).strip()
            p_desc = _node_text(cells[desc_idx]).strip()
            if p_name:
                patterns.append(TestPattern(name=p_name, keyword=p_kw, description=p_desc))
    return patterns


def _parse_traits(nodes: list[dict[str, Any]]) -> list[Trait]:
    """Extract trait definitions from Section 3 nodes."""
    traits: list[Trait] = []
    current_trait: Trait | None = None
    section_mode = False
    gherkin_accumulating = False
    gherkin_lines: list[str] = []
    in_detection = False
    in_patterns = False
    detection_nodes: list[dict[str, Any]] = []
    pattern_nodes: list[dict[str, Any]] = []

    for node in nodes:
        node_type = node.get("type", "")

        if node_type == "heading":
            level = node.get("attrs", {}).get("level", 0)
            text = _ast_nodes_text(node.get("children", [])).strip()

            if level == 3:
                # Save previous trait
                if current_trait is not None:
                    if gherkin_lines:
                        current_trait.gherkin_template = "\n".join(gherkin_lines).strip()
                    if detection_nodes:
                        current_trait.detection_signals = _parse_detection_signals(
                            detection_nodes
                        )
                    if pattern_nodes:
                        current_trait.test_patterns = _parse_test_patterns(pattern_nodes)
                    traits.append(current_trait)

                current_trait = Trait(name=text, description="")
                gherkin_accumulating = False
                gherkin_lines = []
                in_detection = False
                in_patterns = False
                detection_nodes = []
                pattern_nodes = []
                section_mode = True
                continue

            if section_mode and level == 4:
                in_detection = False
                in_patterns = False
                if "gherkin" in text.lower() or "template" in text.lower():
                    gherkin_accumulating = True
                elif "detection signals" in text.lower():
                    in_detection = True
                    gherkin_accumulating = False
                elif "test patterns" in text.lower():
                    in_patterns = True
                    gherkin_accumulating = False
                continue

            # Paragraph-level strong markers
            section_mode = False

        if current_trait is not None:
            # Detect description (first paragraph after H3)
            if not current_trait.description and node_type == "paragraph":
                desc_text = _ast_nodes_text(node.get("children", [])).strip()
                if desc_text and not desc_text.startswith("**"):
                    current_trait.description = desc_text

            # Collect paragraph strong markers like **Detection signals:**
            if node_type == "paragraph":
                para_text = _ast_nodes_text(node.get("children", [])).lower()
                if "detection signals" in para_text:
                    in_detection = True
                    in_patterns = False
                    gherkin_accumulating = False
                    continue
                elif "test patterns" in para_text:
                    in_patterns = True
                    in_detection = False
                    gherkin_accumulating = False
                    continue
                elif "gherkin template" in para_text:
                    gherkin_accumulating = True
                    in_detection = False
                    in_patterns = False
                    continue

            if in_detection:
                detection_nodes.append(node)
            elif in_patterns:
                pattern_nodes.append(node)
            elif gherkin_accumulating and node_type == "block_code":
                raw = node.get("raw", "")
                gherkin_lines.append(raw)

    # Save last trait
    if current_trait is not None:
        if gherkin_lines:
            current_trait.gherkin_template = "\n".join(gherkin_lines).strip()
        if detection_nodes:
            current_trait.detection_signals = _parse_detection_signals(detection_nodes)
        if pattern_nodes:
            current_trait.test_patterns = _parse_test_patterns(pattern_nodes)
        traits.append(current_trait)

    return traits


def _parse_transversal_patterns(nodes: list[dict[str, Any]]) -> list[TransversalPattern]:
    """Extract transversal patterns from Section 4 nodes."""
    patterns: list[TransversalPattern] = []
    current: TransversalPattern | None = None
    gherkin_lines: list[str] = []

    for node in nodes:
        node_type = node.get("type", "")

        if node_type == "heading":
            level = node.get("attrs", {}).get("level", 0)
            text = _ast_nodes_text(node.get("children", [])).strip()

            if level == 3:
                if current is not None:
                    current.combined_gherkin_template = "\n".join(gherkin_lines).strip()
                    patterns.append(current)
                current = TransversalPattern(name=text)
                gherkin_lines = []
                continue

        if current is not None:
            if node_type == "paragraph":
                para_text = _ast_nodes_text(node.get("children", [])).strip()
                if "**constituent traits:**" in para_text.lower():
                    # Extract trait names from inline code spans
                    trait_names = re.findall(r"`([^`]+)`", para_text)
                    current.constituent_traits = [n.strip() for n in trait_names if n.strip()]
                elif "**disambiguation:**" in para_text.lower():
                    current.disambiguation = para_text

            if node_type == "block_code":
                gherkin_lines.append(node.get("raw", ""))

    if current is not None:
        current.combined_gherkin_template = "\n".join(gherkin_lines).strip()
        patterns.append(current)

    return patterns


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


# @spec FR-001, FR-002: load_taxonomy — parse taxonomy, cache, path resolution
def load_taxonomy(path: Path | None = None) -> Taxonomy:
    """Parse the UI behavioral taxonomy Markdown and return a Taxonomy object.

    The result is cached per resolved path. Unknown sections are skipped with a
    DEBUG log (EC-003).

    Args:
        path: Override the default taxonomy path (useful for tests / CI).

    Returns:
        Parsed Taxonomy with traits and transversal_patterns.

    Raises:
        TaxonomyLoadError: If the file is missing or cannot be parsed.
    """
    resolved = (path or _TAXONOMY_PATH).resolve()

    if resolved in _TAXONOMY_CACHE:
        return _TAXONOMY_CACHE[resolved]

    if not resolved.exists():
        raise TaxonomyLoadError(str(resolved))

    try:
        raw_md = resolved.read_text(encoding="utf-8")
    except OSError as exc:
        raise TaxonomyLoadError(str(resolved), str(exc)) from exc

    # Strip YAML frontmatter manually (mistune does not handle it)
    if raw_md.startswith("---"):
        end = raw_md.find("\n---", 3)
        if end != -1:
            raw_md = raw_md[end + 4 :]

    try:
        md = mistune.create_markdown(renderer="ast", plugins=["table"])
        ast: list[dict[str, Any]] = md(raw_md)  # type: ignore[assignment]
    except Exception as exc:
        raise TaxonomyLoadError(str(resolved), f"parse failure: {exc}") from exc

    # Locate Section 3 (Trait Definitions) and Section 4 (Transversal Patterns)
    section3_nodes: list[dict[str, Any]] = []
    section4_nodes: list[dict[str, Any]] = []
    current_section: int = 0

    for node in ast:
        node_type = node.get("type", "")
        if node_type == "heading":
            level = node.get("attrs", {}).get("level", 0)
            text = _ast_nodes_text(node.get("children", [])).strip().lower()
            if level == 2 and "trait definitions" in text:
                current_section = 3
                continue
            if level == 2 and "transversal patterns" in text:
                current_section = 4
                continue
            if level == 2 and current_section in (3, 4):
                # New unrelated H2 — stop collecting
                current_section = 0

        if current_section == 3:
            section3_nodes.append(node)
        elif current_section == 4:
            section4_nodes.append(node)
        else:
            logger.debug("Skipping AST node outside known sections: %s", node.get("type"))

    traits = _parse_traits(section3_nodes)
    transversal = _parse_transversal_patterns(section4_nodes)

    taxonomy = Taxonomy(traits=traits, transversal_patterns=transversal)
    _TAXONOMY_CACHE[resolved] = taxonomy
    return taxonomy


# @spec FR-003, FR-004: detect_traits — signal to trait mapping + co-occurrence
def detect_traits(signals: list[str], path: Path | None = None) -> set[str]:
    """Map UI signal strings to trait names using the taxonomy detection tables.

    Unambiguous signals inject their trait alone.
    Ambiguous signals require ≥2 UI signals in the input list.
    Co-occurrence rule: if has_overlay is detected, dismissible_layer is checked.

    Args:
        signals: List of UI signal strings extracted from a feature description.
        path: Override taxonomy path (for tests / CI).

    Returns:
        Set of trait names to inject.

    Raises:
        TaxonomyLoadError: If taxonomy file is missing (EC-005 fail-fast).
            Returns empty set immediately when signals == [] without reading the file.
    """
    # EC-005: empty list → return immediately, no file read
    if not signals:
        return set()

    taxonomy = load_taxonomy(path)
    normalised = [s.strip().lower() for s in signals]
    result: set[str] = set()

    for trait in taxonomy.traits:
        _check_trait(trait, normalised, result)

    # FR-004: co-occurrence rule — has_overlay co-implies dismissible_layer check
    if "has_overlay" in result:
        dismissible = taxonomy.trait_by_name("dismissible_layer")
        if dismissible:
            _check_trait(dismissible, normalised, result)

    return result


def _check_trait(trait: Trait, normalised_signals: list[str], result: set[str]) -> None:
    """Check whether a trait should be injected given the normalised signal list."""
    if trait.name in result:
        return

    for signal in trait.detection_signals:
        if signal.text not in normalised_signals:
            continue
        if signal.unambiguous:
            result.add(trait.name)
            return
        # Ambiguous: requires ≥2 UI signals total
        if len(normalised_signals) >= 2:
            result.add(trait.name)
            return


# ---------------------------------------------------------------------------
# Deduplication helpers
# ---------------------------------------------------------------------------

_AC_PATTERN: re.Pattern[str] = re.compile(r"^(AC-\d+):\s*(.+)", re.IGNORECASE)
_STOPWORDS: frozenset[str] = frozenset(
    {
        "le", "la", "les", "un", "une", "des", "et", "ou", "de", "du", "avec",
        "the", "a", "an", "of", "and", "or", "is", "are", "in", "on", "to",
        "for", "that", "this", "it", "be", "has", "have", "by",
    }
)


def _tokenise(text: str) -> set[str]:
    """Lowercase word tokens, stopwords removed."""
    words = re.findall(r"\b[a-zA-ZÀ-ÿ]+\b", text.lower())
    return {w for w in words if w not in _STOPWORDS and len(w) > 2}


def _has_overlap(text_a: str, text_b: str) -> bool:
    """Return True if the two texts share at least one content token."""
    return bool(_tokenise(text_a) & _tokenise(text_b))


# @spec FR-005, FR-006: deduplicate_tests — EC-002 overlap merge + EC-004 trait dedup
def deduplicate_tests(
    ac_list: list[str],
    behavioral_ac_list: list[str],
    path: Path | None = None,
) -> list[MergedTest]:
    """Merge overlapping AC and Behavioral AC entries into combined MergedTest items.

    EC-002: overlapping AC + behavioral AC → single MergedTest with combined ref.
    EC-004: duplicate trait entries in behavioral_ac_list injected only once.

    Args:
        ac_list: Manual AC lines, each formatted as "AC-NNN: <text>".
        behavioral_ac_list: Behavioral AC lines, each formatted as "<trait>: <text>".
        path: Override taxonomy path (unused here but accepted for API consistency).

    Returns:
        List of MergedTest items.
    """
    # Parse manual ACs
    ac_structs: list[tuple[str, str]] = []  # (ac_id, text)
    for item in ac_list:
        m = _AC_PATTERN.match(item.strip())
        if m:
            ac_structs.append((m.group(1), m.group(2)))
        else:
            # AC without ID — treat as standalone
            ac_structs.append(("", item.strip()))

    consumed_ac: set[int] = set()
    seen_traits: set[str] = set()
    merged: list[MergedTest] = []

    # EC-004: deduplicate behavioral entries by trait name
    deduplicated_behavioral: list[tuple[str, str]] = []
    for item in behavioral_ac_list:
        if ": " in item:
            trait_part, text_part = item.split(": ", 1)
        else:
            trait_part = item.strip()
            text_part = ""
        trait_part = trait_part.strip()
        if trait_part not in seen_traits:
            seen_traits.add(trait_part)
            deduplicated_behavioral.append((trait_part, text_part))

    seen_traits.clear()

    for b_trait, b_text in deduplicated_behavioral:
        if b_trait in seen_traits:
            continue
        seen_traits.add(b_trait)

        # EC-002: look for keyword overlap with manual ACs
        match_idx: int | None = None
        for idx, (_ac_id, ac_text) in enumerate(ac_structs):
            if idx in consumed_ac:
                continue
            if _has_overlap(ac_text, b_text):
                match_idx = idx
                break

        if match_idx is not None:
            ac_id, _ac_text = ac_structs[match_idx]
            consumed_ac.add(match_idx)
            ref = f"{ac_id} / Behavioral-{b_trait}" if ac_id else f"Behavioral-{b_trait}"
            merged.append(
                MergedTest(
                    ref=ref,
                    behavioral_trait=b_trait,
                    ac_id=ac_id or None,
                    gherkin="",
                )
            )
        else:
            merged.append(
                MergedTest(
                    ref=f"Behavioral-{b_trait}",
                    behavioral_trait=b_trait,
                    ac_id=None,
                    gherkin="",
                )
            )

    # Unconsumed manual ACs → standalone MergedTest
    for idx, (ac_id, _ac_text) in enumerate(ac_structs):
        if idx not in consumed_ac:
            merged.append(
                MergedTest(
                    ref=ac_id if ac_id else _ac_text,
                    behavioral_trait=None,
                    ac_id=ac_id or None,
                    gherkin="",
                )
            )

    return merged
