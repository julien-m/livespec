"""R1 — Roadmap / Features coherence rules."""

from __future__ import annotations

from pathlib import Path

from validator.coherence.graph_builder import SpecGraph
from validator.coherence.violation import Severity, Violation


class R1_1_RoadmapFeatureMissing:
    """Checked roadmap item links to a feature directory that does not exist."""

    rule_id = "R1.1"
    description = "Roadmap item links to a missing feature directory"
    wave = 1

    def check(self, graph: SpecGraph, specs_root: Path) -> list[Violation]:
        """Check that checked roadmap items link to existing feature directories.

        Args:
            graph: SpecGraph containing roadmap and feature data.
            specs_root: Root directory of the .specs/ tree.

        Returns:
            List of violations for roadmap items linking to missing features.
        """
        violations: list[Violation] = []
        for item in graph.roadmap:
            if not item.checked or not item.link or "features/" not in item.link:
                continue
            # Extract dir_name from the link
            dir_name = item.link.split("features/")[-1].split("/")[0]
            if graph.get_feature(dir_name) is None:
                violations.append(
                    Violation(
                        rule_id=self.rule_id,
                        severity=Severity.ERROR,
                        message=(
                            f"Roadmap item '{item.name}' (line {item.line_number}) "
                            f"links to features/{dir_name} which does not exist"
                        ),
                        context={"roadmap_item": item.name, "dir_name": dir_name},
                        fix_hint=f"Create features/{dir_name}/ or fix the roadmap link",
                        suppress_if_creating=False,
                    )
                )
        return violations


class R1_2_OrphanFeature:
    """Feature directory exists but is not referenced in any roadmap item."""

    rule_id = "R1.2"
    description = "Feature directory not referenced in roadmap"
    wave = 1

    def check(self, graph: SpecGraph, specs_root: Path) -> list[Violation]:
        """Check that every feature directory is referenced in the roadmap.

        Args:
            graph: SpecGraph containing roadmap and feature data.
            specs_root: Root directory of the .specs/ tree.

        Returns:
            List of violations for orphan feature directories.
        """
        violations: list[Violation] = []
        # Collect all dir_names and slugs referenced by roadmap items
        roadmap_refs: set[str] = set()
        for item in graph.roadmap:
            roadmap_refs.add(item.slug)
            if item.link and "features/" in item.link:
                dir_name = item.link.split("features/")[-1].split("/")[0]
                roadmap_refs.add(dir_name)

        for feature in graph.features:
            if feature.dir_name not in roadmap_refs and feature.slug not in roadmap_refs:
                violations.append(
                    Violation(
                        rule_id=self.rule_id,
                        severity=Severity.WARNING,
                        message=(
                            f"Feature '{feature.dir_name}' is not referenced in any roadmap item"
                        ),
                        context={"dir_name": feature.dir_name},
                        fix_hint=f"Add features/{feature.dir_name} to roadmap.md",
                        suppress_if_creating=True,
                    )
                )
        return violations


class R1_3_StatusRoadmapMismatch:
    """Feature status does not match its roadmap checked state."""

    rule_id = "R1.3"
    description = "Feature status conflicts with roadmap checked/unchecked state"
    wave = 1

    def check(self, graph: SpecGraph, specs_root: Path) -> list[Violation]:
        """Check that feature status matches roadmap checked state.

        Args:
            graph: SpecGraph containing roadmap and feature data.
            specs_root: Root directory of the .specs/ tree.

        Returns:
            List of violations where status conflicts with roadmap state.
        """
        violations: list[Violation] = []
        for item in graph.roadmap:
            if not item.link or "features/" not in item.link:
                continue

            dir_name = item.link.split("features/")[-1].split("/")[0]
            feature = graph.get_feature(dir_name)
            if feature is None or feature.status is None:
                continue

            status = feature.status
            if status == "Deprecated":
                continue

            if status == "Implemented" and not item.checked:
                violations.append(
                    Violation(
                        rule_id=self.rule_id,
                        severity=Severity.ERROR,
                        message=(
                            f"Feature '{dir_name}' has status '{status}' "
                            f"but roadmap item '{item.name}' is unchecked"
                        ),
                        context={
                            "dir_name": dir_name,
                            "status": status,
                            "checked": item.checked,
                        },
                        fix_hint="Check the roadmap item or update the feature status",
                        suppress_if_creating=True,
                    )
                )
        return violations


class R1_4_CheckedNoLink:
    """Roadmap item is checked but has no link to features/."""

    rule_id = "R1.4"
    description = "Checked roadmap item has no feature link"
    wave = 1

    def check(self, graph: SpecGraph, specs_root: Path) -> list[Violation]:
        """Check that checked roadmap items have a feature link.

        Args:
            graph: SpecGraph containing roadmap and feature data.
            specs_root: Root directory of the .specs/ tree.

        Returns:
            List of violations for checked items without links.
        """
        violations: list[Violation] = []
        for item in graph.roadmap:
            if not item.checked:
                continue
            if not item.link or "features/" not in item.link:
                violations.append(
                    Violation(
                        rule_id=self.rule_id,
                        severity=Severity.WARNING,
                        message=(
                            f"Roadmap item '{item.name}' (line {item.line_number}) "
                            f"is checked but has no link to features/"
                        ),
                        context={"roadmap_item": item.name, "line_number": item.line_number},
                        fix_hint="Add a [name](features/NNN-slug/) link to the roadmap item",
                        suppress_if_creating=False,
                    )
                )
        return violations
