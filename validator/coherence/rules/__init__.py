"""Registry of all coherence validation rules."""

from __future__ import annotations

from validator.coherence.rules.r1_roadmap_features import (
    R1_1_RoadmapFeatureMissing,
    R1_2_OrphanFeature,
    R1_3_StatusRoadmapMismatch,
    R1_4_CheckedNoLink,
)
from validator.coherence.rules.r2_status_files import (
    R2_1_RequiredFileAbsent,
    R2_2_AdvancedFileForLowStatus,
    R2_3_InvalidStatus,
)
from validator.coherence.rules.r3_spec_anchors import (
    R3_1_SourceFileNotFound,
    R3_2_SpecAnchorMissing,
)
from validator.coherence.rules.r4_readme_sync import (
    R4_1_ReadmeFeatureMissing,
    R4_2_DiskFeatureMissingReadme,
    R4_3_ReadmeStatusMismatch,
)
from validator.coherence.rules.r5_stack_preflight import R5_1_StackNoPreflight
from validator.coherence.rules.r6_changelog_refs import R6_1_ChangelogFeatureMissing

ALL_RULES: list = [
    R1_1_RoadmapFeatureMissing(),
    R1_2_OrphanFeature(),
    R1_3_StatusRoadmapMismatch(),
    R1_4_CheckedNoLink(),
    R2_1_RequiredFileAbsent(),
    R2_2_AdvancedFileForLowStatus(),
    R2_3_InvalidStatus(),
    R3_1_SourceFileNotFound(),
    R3_2_SpecAnchorMissing(),
    R4_1_ReadmeFeatureMissing(),
    R4_2_DiskFeatureMissingReadme(),
    R4_3_ReadmeStatusMismatch(),
    R5_1_StackNoPreflight(),
    R6_1_ChangelogFeatureMissing(),
]


def get_rules(
    wave: int | None = None,
    rule_ids: list[str] | None = None,
    ignore: list[str] | None = None,
) -> list:
    """Filter rules by wave, explicit IDs, or ignore list."""
    rules = ALL_RULES

    if wave is not None:
        rules = [r for r in rules if r.wave <= wave]

    if rule_ids is not None:
        id_set = set(rule_ids)
        rules = [
            r for r in rules
            if r.rule_id in id_set or any(r.rule_id.startswith(rid) for rid in id_set)
        ]

    if ignore is not None:
        ignore_set = set(ignore)
        rules = [r for r in rules if r.rule_id not in ignore_set]

    return rules
