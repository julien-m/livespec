"""Orchestrate coherence rules by wave order."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path

from .graph_builder import SpecGraph, build_graph
from .violation import Severity, Violation


@dataclass
class CoherenceResult:
    """Result of a coherence validation run."""

    graph: SpecGraph
    violations: list[Violation] = field(default_factory=list)
    suppressed: list[Violation] = field(default_factory=list)

    @property
    def errors(self) -> list[Violation]:
        """Filter violations by ERROR severity."""
        return [v for v in self.violations if v.severity == Severity.ERROR]

    @property
    def warnings(self) -> list[Violation]:
        """Filter violations by WARNING severity."""
        return [v for v in self.violations if v.severity == Severity.WARNING]

    @property
    def infos(self) -> list[Violation]:
        """Filter violations by INFO severity."""
        return [v for v in self.violations if v.severity == Severity.INFO]

    @property
    def has_errors(self) -> bool:
        """Return True if any ERROR-level violations exist."""
        return len(self.errors) > 0


def run_coherence(
    specs_root: Path,
    rule_ids: list[str] | None = None,
    wave: int | None = None,
    ignore: list[str] | None = None,
    no_suppress: bool = False,
    strict: bool = False,
) -> CoherenceResult:
    """Run coherence validation on .specs/ directory.

    Args:
        specs_root: Path to .specs/ directory
        rule_ids: Only run these specific rules (e.g., ["R1", "R2"])
        wave: Only run rules from this wave
        ignore: Skip these rules (e.g., ["R3.2", "R5.1"])
        no_suppress: Disable suppress_if_creating
        strict: Treat warnings as errors for exit code

    Returns:
        CoherenceResult with all violations and suppressed items.
    """
    from .rules import get_rules

    # Build graph
    graph = build_graph(specs_root)

    # Get filtered rules
    rules = get_rules(wave=wave, rule_ids=rule_ids, ignore=ignore)

    # Sort by wave for ordered execution
    rules.sort(key=lambda r: r.wave)

    result = CoherenceResult(graph=graph)

    now = time.time()
    suppress_threshold = 30 * 60  # 30 minutes

    for rule in rules:
        violations = rule.check(graph, specs_root)

        for v in violations:
            # Apply suppress_if_creating
            if v.suppress_if_creating and not no_suppress:
                # Find the feature this violation relates to
                feature_dir = v.context.get("feature_dir")
                if isinstance(feature_dir, str) and feature_dir:
                    feature = graph.get_feature(feature_dir)
                    if feature and feature.spec_mtime:
                        age = now - feature.spec_mtime
                        if age < suppress_threshold:
                            minutes = int(age / 60)
                            v.severity = Severity.INFO
                            v.message = f"[in-progress, {minutes}min] {v.message}"
                            result.suppressed.append(v)
                            continue

            result.violations.append(v)

    return result
