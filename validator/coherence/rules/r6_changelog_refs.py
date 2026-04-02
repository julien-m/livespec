"""R6 — Changelog rules: verify changelog feature references are valid."""

from __future__ import annotations

from validator.coherence.graph_builder import SpecGraph
from validator.coherence.violation import Severity, Violation


class R6_1_ChangelogFeatureMissing:
    """Check that every feature reference in changelog.md matches an existing feature directory."""

    rule_id = "R6.1"
    description = "Changelog references a feature that does not exist in features/"
    wave = 2

    def check(self, graph: SpecGraph) -> list[Violation]:
        if not graph.changelog_refs:
            return []

        known_dirs = graph.feature_dirs
        violations: list[Violation] = []

        for ref in graph.changelog_refs:
            if ref not in known_dirs:
                violations.append(
                    Violation(
                        rule_id=self.rule_id,
                        severity=Severity.WARNING,
                        message=(
                            f"Changelog references feature '{ref}' "
                            f"which does not exist in features/"
                        ),
                        context={"ref": ref},
                        fix_hint=(
                            f"Create .specs/features/{ref}/ or fix the "
                            f"reference in .specs/changelog.md"
                        ),
                        suppress_if_creating=False,
                    )
                )

        return violations
