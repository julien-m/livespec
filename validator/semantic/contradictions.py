"""Contradiction detection between spec artifacts."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from validator.coherence.graph_builder import SpecGraph
from validator.coherence.violation import Severity


@dataclass
class Assertion:
    """A single extracted assertion from a spec artifact."""

    id: str
    theme: str
    assertion_text: str
    polarity: str  # "must" | "must-not" | "may"
    source_file: str
    source_line: int


@dataclass
class ContradictionResult:
    """Result of comparing two assertions."""

    contradicts: bool
    confidence: float
    explanation: str
    severity: Severity  # ERROR (blocking), WARNING, INFO


@dataclass
class ContradictionReport:
    """Summary of contradiction analysis across a spec tree."""

    pairs_checked: int
    contradictions: list[ContradictionResult] = field(default_factory=list)
    suspicions: list[ContradictionResult] = field(default_factory=list)


def extract_assertions(content: str, source_file: str) -> list[Assertion]:
    """Extract semantic assertions from spec content.

    STUB: requires LLM-based assertion extraction.
    """
    raise NotImplementedError(
        "LLM assertion extraction not configured. "
        "This feature requires an LLM API to parse natural-language requirements "
        "into structured assertions."
    )


def compare_assertions(a: Assertion, b: Assertion) -> ContradictionResult:
    """Compare two assertions for semantic contradiction.

    STUB: requires LLM-based semantic comparison.
    """
    raise NotImplementedError(
        "LLM assertion comparison not configured. "
        "This feature requires an LLM API to detect semantic contradictions "
        "between assertions."
    )


def get_comparison_pairs(graph: SpecGraph) -> list[tuple[str, str]]:
    """Determine which file pairs need contradiction checking.

    Comparison rules:
    - constitution x every spec and plan
    - stack x every spec and plan
    - spec x plan for the same feature
    - spec x spec when features share themes (adjacent numbering as proxy)
    """
    pairs: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()

    def _add(a: str, b: str) -> None:
        key = (min(a, b), max(a, b))
        if key not in seen and a != b:
            seen.add(key)
            pairs.append(key)

    # Global files to compare against all features
    global_files = ["constitution.md", "stacks/_default.md"]

    feature_specs: list[str] = []
    feature_plans: list[str] = []

    for feat in graph.features:
        spec_path = f"features/{feat.dir_name}/spec.md"
        plan_path = f"features/{feat.dir_name}/plan.md"

        has_spec = feat.files.get("spec", False)
        has_plan = feat.files.get("plan", False)

        if has_spec:
            feature_specs.append(spec_path)
        if has_plan:
            feature_plans.append(plan_path)

        # Rule: constitution and stack x every spec and plan
        for gf in global_files:
            if has_spec:
                _add(gf, spec_path)
            if has_plan:
                _add(gf, plan_path)

        # Rule: spec x plan for the same feature
        if has_spec and has_plan:
            _add(spec_path, plan_path)

    # Rule: spec x spec for adjacent features (shared themes proxy)
    sorted_features = sorted(graph.features, key=lambda f: f.num)
    for i in range(len(sorted_features) - 1):
        curr = sorted_features[i]
        next_feat = sorted_features[i + 1]
        if curr.files.get("spec", False) and next_feat.files.get("spec", False):
            _add(
                f"features/{curr.dir_name}/spec.md",
                f"features/{next_feat.dir_name}/spec.md",
            )

    return pairs
