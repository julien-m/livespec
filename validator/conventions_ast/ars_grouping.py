# @spec FR-003: One violation per file and shared detector
#   .specs/features/082-conventions-gate-signal/spec.md#fr-003

"""Group executable ARS matches per file: one violation per shared family detector."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Protocol

from validator.conventions_gate_types import GateSeverity, GateViolation

FAMILY_RULE_PREFIX = "ars.family."
# Family messages name the first few inventory ids; `rule_ids` carries the full list.
_LISTED_IDS = 3

GroupKey = tuple[str, str]


class GroupableRule(Protocol):
    """Rule fields needed to describe a grouped violation."""

    @property
    def inventory_id(self) -> str: ...

    @property
    def runtime_rule_id(self) -> str: ...

    @property
    def rule_text(self) -> str: ...

    @property
    def source_path(self) -> str: ...

    @property
    def source_anchor(self) -> str: ...


class GroupableDetector(Protocol):
    """Detector fields needed to evaluate and group a match."""

    @property
    def rule(self) -> GroupableRule: ...

    @property
    def helper(self) -> Callable[[str], bool]: ...

    @property
    def family_key(self) -> str | None: ...


def group_file_matches(
    rel: str, text: str, detectors: Sequence[GroupableDetector]
) -> list[GateViolation]:
    """Evaluate applicable detectors once per shared helper and group their matches.

    Args:
        rel: Project-relative path reported on violations.
        text: File content.
        detectors: Detectors already filtered for language and framework applicability.

    Returns:
        One violation per matched shared family detector and per matched rule-specific detector.
    """
    outcomes: dict[int, bool] = {}
    groups: dict[GroupKey, list[GroupableDetector]] = {}
    for detector in detectors:
        key = id(detector.helper)
        if key not in outcomes:
            outcomes[key] = detector.helper(text)
        if outcomes[key]:
            groups.setdefault(_group_key(detector), []).append(detector)
    return [_grouped_violation(rel, text, matched) for _key, matched in sorted(groups.items())]


def first_matching_line(text: str, detector: Callable[[str], bool]) -> int:
    """Return the first 1-based line matched by a detector, or 1 for multi-line matches."""
    for index, line in enumerate(text.splitlines(), start=1):
        if detector(line):
            return index
    return 1


def _group_key(detector: GroupableDetector) -> GroupKey:
    if detector.family_key is not None:
        return ("family", detector.family_key)
    return ("rule", detector.rule.inventory_id)


def _grouped_violation(rel: str, text: str, detectors: list[GroupableDetector]) -> GateViolation:
    first = detectors[0]
    rules = sorted((detector.rule for detector in detectors), key=lambda rule: rule.inventory_id)
    rule_ids = tuple(sorted(rule.runtime_rule_id for rule in rules))
    line = first_matching_line(text, first.helper)
    if first.family_key is None:
        return GateViolation(
            rule_id=first.rule.runtime_rule_id,
            path=rel,
            line=line,
            severity=GateSeverity.ERROR,
            message=f"{first.rule.inventory_id}: {first.rule.rule_text}",
            source="ars",
            fix_hint=f"See {first.rule.source_path}{first.rule.source_anchor}",
            rule_ids=rule_ids,
        )
    return GateViolation(
        rule_id=f"{FAMILY_RULE_PREFIX}{first.family_key}",
        path=rel,
        line=line,
        severity=GateSeverity.ERROR,
        message=_family_message(first.family_key, [rule.inventory_id for rule in rules]),
        source="ars",
        fix_hint="See " + ", ".join(sorted({rule.source_path for rule in rules})),
        rule_ids=rule_ids,
    )


def _family_message(family: str, inventory_ids: list[str]) -> str:
    listed = ", ".join(inventory_ids[:_LISTED_IDS])
    more = len(inventory_ids) - _LISTED_IDS
    suffix = f", +{more} more" if more > 0 else ""
    return f"ARS family {family}: {len(inventory_ids)} matched rule(s) ({listed}{suffix})"
