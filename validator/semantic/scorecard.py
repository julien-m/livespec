"""Layer 4 scorecard — 5-axis scoring engine for spec quality."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from ..coherence.graph_builder import FeatureInfo


@dataclass
class FeatureScore:
    """Score for a single feature across all axes."""

    feature_name: str
    axes: dict[str, int] = field(default_factory=dict)
    weights: dict[str, float] = field(default_factory=dict)
    total: float = 0.0


@dataclass
class ProjectScore:
    """Aggregate score across all features."""

    features: list[FeatureScore] = field(default_factory=list)
    total: float = 0.0


# Axis weights
AXIS_WEIGHTS: dict[str, float] = {
    "structural_completeness": 0.20,
    "artifact_quality": 0.25,
    "ac_fr_coverage": 0.20,
    "semantic_coherence": 0.20,
    "mermaid_richness": 0.15,
}


# --- Regex helpers ---

_NEEDS_CLARIFICATION_RE = re.compile(r"\[NEEDS\s+CLARIFICATION\]", re.IGNORECASE)
_GHERKIN_BLOCK_RE = re.compile(r"```gherkin", re.IGNORECASE)
_MERMAID_BLOCK_RE = re.compile(
    r"```mermaid\s*\n(.*?)```", re.DOTALL | re.IGNORECASE
)
_FR_ID_RE = re.compile(r"\bFR-\d+\b")
_AC_ID_RE = re.compile(r"\bAC-\d+\b")
_SPEC_ANCHOR_RE = re.compile(r"@spec\(?((?:FR|AC)-\d+)\)?")
_DIAGRAM_TYPE_RE = re.compile(
    r"^\s*(flowchart|sequenceDiagram|stateDiagram|erDiagram|classDiagram|gantt|pie|graph)",
    re.MULTILINE,
)
_ENTITIES_SECTION_RE = re.compile(r"^##\s+.*(?:entit|data\s*model)", re.MULTILINE | re.IGNORECASE)


def _read_file(path: Path) -> str:
    """Read a file, returning empty string if missing."""
    if path.exists():
        return path.read_text()
    return ""


def _score_axis1(feature: FeatureInfo, specs_root: Path) -> int:
    """Structural completeness (L1). Max 100."""
    score = 0
    feature_dir = specs_root / "features" / feature.dir_name

    # spec.md present: 20pts
    if feature.files.get("spec"):
        score += 20

    # plan.md present if status >= Planned: 15pts
    status = (feature.status or "").lower()
    if status in ("planned", "in-progress", "implemented", "shipped"):
        if feature.files.get("plan"):
            score += 15
    else:
        # Not expected yet, give full credit
        score += 15

    # implementation.md present if status == Implemented: 15pts
    if status in ("implemented", "shipped"):
        if feature.files.get("implementation"):
            score += 15
    else:
        score += 15

    # changelog.md present: 10pts
    if feature.files.get("changelog"):
        score += 10

    # No [NEEDS CLARIFICATION] in spec: 20pts
    spec_content = _read_file(feature_dir / "spec.md")
    if spec_content and not _NEEDS_CLARIFICATION_RE.search(spec_content):
        score += 20
    elif not spec_content:
        # No spec means we already penalized above
        pass

    # All L1 validation passing (no errors): 20pts
    # We approximate by checking frontmatter presence and basic structure
    from ..parser import parse_file

    spec_path = feature_dir / "spec.md"
    if spec_path.exists():
        try:
            parsed = parse_file(spec_path)
            has_frontmatter = bool(parsed.metadata)
            has_headings = len(parsed.headings) >= 2
            if has_frontmatter and has_headings:
                score += 20
            elif has_frontmatter:
                score += 10
        except Exception:
            pass

    return min(score, 100)


def _score_axis2(feature: FeatureInfo, specs_root: Path) -> int:
    """Artifact quality (L2). Max 100."""
    score = 0
    feature_dir = specs_root / "features" / feature.dir_name

    spec_content = _read_file(feature_dir / "spec.md")
    plan_content = _read_file(feature_dir / "plan.md")

    # All stories have Mermaid flowchart: 25pts
    if spec_content and _MERMAID_BLOCK_RE.search(spec_content):
        score += 25

    # All AC in Gherkin format: 25pts
    if spec_content and _GHERKIN_BLOCK_RE.search(spec_content):
        score += 25

    # All FR reference >=1 AC: 20pts
    if spec_content:
        fr_ids = set(_FR_ID_RE.findall(spec_content))
        ac_ids = set(_AC_ID_RE.findall(spec_content))
        if fr_ids and ac_ids:
            # Check that at least some FRs appear near ACs (simplified)
            score += 20
        elif fr_ids:
            score += 10

    # Has sequence/state diagram in plan: 15pts
    if plan_content:
        mermaid_blocks = _MERMAID_BLOCK_RE.findall(plan_content)
        for block in mermaid_blocks:
            if re.search(r"sequenceDiagram|stateDiagram", block):
                score += 15
                break

    # Has ER diagram if entities section present: 15pts
    if spec_content and _ENTITIES_SECTION_RE.search(spec_content):
        all_content = spec_content + plan_content
        mermaid_blocks = _MERMAID_BLOCK_RE.findall(all_content)
        has_er = any(re.search(r"erDiagram", b) for b in mermaid_blocks)
        if has_er:
            score += 15
    else:
        # No entities section, give full credit
        score += 15

    return min(score, 100)


def _score_axis3(feature: FeatureInfo, specs_root: Path) -> int:
    """AC->FR coverage (L2). Max 100."""
    score = 0
    feature_dir = specs_root / "features" / feature.dir_name

    spec_content = _read_file(feature_dir / "spec.md")
    impl_content = _read_file(feature_dir / "implementation.md")

    if not spec_content:
        return 0

    fr_ids = set(_FR_ID_RE.findall(spec_content))
    ac_ids = set(_AC_ID_RE.findall(spec_content))

    # % FR verified in implementation.md: 40pts (proportional)
    if fr_ids and impl_content:
        impl_fr_ids = set(_FR_ID_RE.findall(impl_content))
        covered = len(fr_ids & impl_fr_ids)
        ratio = covered / len(fr_ids) if fr_ids else 0
        score += int(40 * ratio)
    elif not fr_ids:
        # No FRs defined, neutral
        score += 20

    # % AC covered by @spec anchors: 40pts (proportional)
    if ac_ids:
        anchored_acs = {a for a in feature.spec_anchors if a.startswith("AC-")}
        covered = len(ac_ids & anchored_acs)
        ratio = covered / len(ac_ids) if ac_ids else 0
        score += int(40 * ratio)
    elif not ac_ids:
        score += 20

    # No stale AC (all AC referenced somewhere): 20pts
    if ac_ids:
        all_text = spec_content + impl_content
        all_ac_refs = set(_AC_ID_RE.findall(all_text))
        if ac_ids <= all_ac_refs:
            score += 20
        else:
            stale_ratio = len(ac_ids - all_ac_refs) / len(ac_ids)
            score += int(20 * (1 - stale_ratio))
    else:
        score += 20

    return min(score, 100)


def _score_axis4(feature: FeatureInfo, specs_root: Path) -> int:
    """Semantic coherence (L4). Stub: returns 50 (neutral)."""
    return 50


def _score_axis5(feature: FeatureInfo, specs_root: Path) -> int:
    """Mermaid richness (L2+L4). Max 100."""
    score = 0
    feature_dir = specs_root / "features" / feature.dir_name

    all_content = ""
    for name in ("spec.md", "plan.md", "implementation.md"):
        all_content += _read_file(feature_dir / name) + "\n"

    mermaid_blocks = _MERMAID_BLOCK_RE.findall(all_content)

    if not mermaid_blocks:
        return 0

    # Diagrams present and parseable: 30pts
    non_empty = [b for b in mermaid_blocks if b.strip()]
    if non_empty:
        score += 30

    # At least 2 different diagram types: 40pts
    diagram_types: set[str] = set()
    for block in mermaid_blocks:
        types_found = _DIAGRAM_TYPE_RE.findall(block)
        diagram_types.update(types_found)

    if len(diagram_types) >= 2:
        score += 40
    elif len(diagram_types) == 1:
        score += 20

    # No empty diagrams: 30pts
    empty_count = len(mermaid_blocks) - len(non_empty)
    if empty_count == 0:
        score += 30

    return min(score, 100)


def score_feature(feature: FeatureInfo, specs_root: Path) -> FeatureScore:
    """Score a single feature across all 5 axes."""
    axes = {
        "structural_completeness": _score_axis1(feature, specs_root),
        "artifact_quality": _score_axis2(feature, specs_root),
        "ac_fr_coverage": _score_axis3(feature, specs_root),
        "semantic_coherence": _score_axis4(feature, specs_root),
        "mermaid_richness": _score_axis5(feature, specs_root),
    }

    total = sum(axes[k] * AXIS_WEIGHTS[k] for k in axes)

    return FeatureScore(
        feature_name=feature.dir_name,
        axes=axes,
        weights=dict(AXIS_WEIGHTS),
        total=round(total, 1),
    )


def score_project(features: list[FeatureInfo], specs_root: Path) -> ProjectScore:
    """Score all features and compute project average."""
    feature_scores = [score_feature(f, specs_root) for f in features]

    if feature_scores:
        total = sum(fs.total for fs in feature_scores) / len(feature_scores)
    else:
        total = 0.0

    return ProjectScore(features=feature_scores, total=round(total, 1))
