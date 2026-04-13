"""R5 — Stack preflight rules: verify stack technologies have preflight checks."""

from __future__ import annotations

from pathlib import Path

from validator.coherence.graph_builder import SpecGraph
from validator.coherence.violation import Severity, Violation


class R5_1_StackNoPreflight:
    """Check that each stack technology is mentioned in at least one preflight check."""

    rule_id = "R5.1"
    description = "Stack technology has no corresponding preflight check"
    wave = 3

    def check(self, graph: SpecGraph, specs_root: Path) -> list[Violation]:
        """Check that stack technologies have preflight checks.

        Args:
            graph: SpecGraph containing stack and preflight data.
            specs_root: Root directory of the .specs/ tree.

        Returns:
            List of violations for stack technologies without preflight checks.
        """
        if not graph.stack_technologies:
            return []

        preflight_text = " ".join(graph.preflight_checks).lower()
        violations: list[Violation] = []

        for tech in graph.stack_technologies:
            if tech.lower() not in preflight_text:
                violations.append(
                    Violation(
                        rule_id=self.rule_id,
                        severity=Severity.INFO,
                        message=(
                            f"Stack technology '{tech}' is not mentioned in any preflight check"
                        ),
                        context={"technology": tech},
                        fix_hint=(
                            f"Add a preflight check for '{tech}' in "
                            f".specs/preflight.md (e.g. version check, auth)"
                        ),
                        suppress_if_creating=False,
                    )
                )

        return violations
