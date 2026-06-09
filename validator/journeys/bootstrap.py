# LiveSpec traceability anchors
# @spec(FR-015)

"""Bootstrap User Journeys v2 candidates from existing LiveSpec projects."""

# @spec FR-015: bootstrap existing specs into candidate cross-feature journeys without writing
# — .specs/features/057-cross-feature-user-journeys-v2/spec.md#fr-015

from __future__ import annotations

import re
from pathlib import Path

from .assignment import JourneyAssignmentCandidate, infer_journey_assignment

_SCENARIO_HINT_RE = re.compile(r"user .+", re.IGNORECASE)


def bootstrap_journey_candidates(project_root: Path) -> list[JourneyAssignmentCandidate]:
    """Return journey candidates inferred from existing specs without writing files.

    Args:
        project_root: Project root containing `.specs/`.

    Returns:
        Candidate journeys for interactive review.
    """
    intents = _candidate_intents(project_root)
    candidates = [infer_journey_assignment(project_root, intent) for intent in intents]
    return [candidate for candidate in candidates if candidate.covers]


def _candidate_intents(project_root: Path) -> list[str]:
    """Extract stable candidate intent lines from existing feature specs."""
    seen: set[str] = set()
    intents: list[str] = []
    for spec_path in sorted((project_root / ".specs" / "features").glob("*/spec.md")):
        for line in spec_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            normalized = line.strip().strip("- ")
            if not normalized:
                continue
            match = _SCENARIO_HINT_RE.search(normalized)
            if match is None:
                continue
            intent = match.group(0).rstrip(".")
            if intent in seen:
                continue
            seen.add(intent)
            intents.append(intent)
    return intents


__all__ = ["bootstrap_journey_candidates"]
