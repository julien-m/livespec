"""Project index for User Journeys v2 sources."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from .models import JourneyFile
from .validator import validate_journeys


@dataclass(frozen=True)
class JourneyIndex:
    """Searchable summary of v2 journeys in a project."""

    journeys: dict[str, JourneyFile] = field(default_factory=dict)
    by_feature: dict[str, set[str]] = field(default_factory=dict)


def build_journey_index(project_root: Path) -> JourneyIndex:
    """Build an index of valid journeys keyed by ID and covered feature.

    Args:
        project_root: Project root containing `.specs/`.

    Returns:
        Journey index built from currently valid v2 journey sources.
    """
    result = validate_journeys(project_root)
    journeys = {journey.journey_id: journey for journey in result.journeys}
    feature_map: defaultdict[str, set[str]] = defaultdict(set)
    for journey in result.journeys:
        for feature in journey.covered_features:
            feature_map[feature].add(journey.journey_id)
    return JourneyIndex(journeys=journeys, by_feature=dict(feature_map))


__all__ = ["JourneyIndex", "build_journey_index"]
