"""R4 — README / Disk sync rules."""

from __future__ import annotations

from pathlib import Path

from validator.coherence.graph_builder import SpecGraph
from validator.coherence.violation import Severity, Violation


class R4_1_ReadmeFeatureMissing:
    """README references a feature directory that does not exist on disk."""

    rule_id = "R4.1"
    description = "README references a non-existent feature directory"
    wave = 1

    def check(self, graph: SpecGraph, specs_root: Path) -> list[Violation]:
        """Check that README feature references exist on disk.

        Args:
            graph: SpecGraph containing README and feature data.
            specs_root: Root directory of the .specs/ tree.

        Returns:
            List of violations for README references to missing features.
        """
        violations: list[Violation] = []
        feature_dirs = graph.feature_dirs
        for entry in graph.readme_entries:
            if entry not in feature_dirs:
                violations.append(
                    Violation(
                        rule_id=self.rule_id,
                        severity=Severity.ERROR,
                        message=(
                            f"README references features/{entry} "
                            f"but the directory does not exist"
                        ),
                        context={"dir_name": entry},
                        fix_hint=f"Create features/{entry}/ or remove the README entry",
                        suppress_if_creating=False,
                    )
                )
        return violations


class R4_2_DiskFeatureMissingReadme:
    """Feature directory exists on disk but is not listed in README."""

    rule_id = "R4.2"
    description = "Feature directory missing from README"
    wave = 1

    def check(self, graph: SpecGraph, specs_root: Path) -> list[Violation]:
        """Check that disk features are listed in README.

        Args:
            graph: SpecGraph containing README and feature data.
            specs_root: Root directory of the .specs/ tree.

        Returns:
            List of violations for features missing from README.
        """
        violations: list[Violation] = []
        readme_set = set(graph.readme_entries)
        for feature in graph.features:
            if feature.dir_name not in readme_set:
                violations.append(
                    Violation(
                        rule_id=self.rule_id,
                        severity=Severity.WARNING,
                        message=(
                            f"Feature '{feature.dir_name}' exists on disk "
                            f"but is not listed in README"
                        ),
                        context={"dir_name": feature.dir_name},
                        fix_hint=f"Add features/{feature.dir_name} to .specs/README.md",
                        suppress_if_creating=True,
                    )
                )
        return violations


class R4_3_ReadmeStatusMismatch:
    """README shows a different status than what spec.md declares."""

    rule_id = "R4.3"
    description = "README status differs from spec.md status"
    wave = 1

    def check(self, graph: SpecGraph, specs_root: Path) -> list[Violation]:
        """Check that README statuses match feature statuses.

        Args:
            graph: SpecGraph containing README and feature status data.
            specs_root: Root directory of the .specs/ tree.

        Returns:
            List of violations for status mismatches between README and spec.
        """
        violations: list[Violation] = []
        for dir_name, readme_status in graph.readme_statuses.items():
            feature = graph.get_feature(dir_name)
            if feature is None or feature.status is None:
                continue

            if readme_status.lower() != feature.status.lower():
                violations.append(
                    Violation(
                        rule_id=self.rule_id,
                        severity=Severity.WARNING,
                        message=(
                            f"Feature '{dir_name}' has status '{feature.status}' "
                            f"in spec.md but '{readme_status}' in README"
                        ),
                        context={
                            "dir_name": dir_name,
                            "spec_status": feature.status,
                            "readme_status": readme_status,
                        },
                        fix_hint="Update README to match the spec.md status",
                        suppress_if_creating=True,
                    )
                )
        return violations
