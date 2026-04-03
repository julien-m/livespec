"""R2 — Status / Files coherence rules."""

from __future__ import annotations

from pathlib import Path

from validator.coherence.graph_builder import SpecGraph
from validator.coherence.violation import Severity, Violation

# Status-to-required-files matrix
_REQUIRED_FILES: dict[str, list[str]] = {
    "Draft": ["spec"],
    "Planned": ["spec", "plan"],
    "In Progress": ["spec", "plan", "progress"],
    "Approved": ["spec", "plan"],
    "Implemented": ["spec", "plan", "implementation"],
    "Deprecated": ["spec"],
    "Review": ["spec"],
}

_VALID_STATUSES: set[str] = set(_REQUIRED_FILES.keys())


class R2_1_RequiredFileAbsent:
    """Required file is missing for the current feature status."""

    rule_id = "R2.1"
    description = "Required file absent for feature status"
    wave = 1

    def check(self, graph: SpecGraph, specs_root: Path) -> list[Violation]:
        """Check that required files exist for the feature's status.

        Args:
            graph: SpecGraph containing feature data.
            specs_root: Root directory of the .specs/ tree.

        Returns:
            List of violations for missing required files.
        """
        violations: list[Violation] = []
        for feature in graph.features:
            if feature.status is None or feature.status not in _REQUIRED_FILES:
                continue

            required = _REQUIRED_FILES[feature.status]
            for file_name in required:
                if not feature.files.get(file_name, False):
                    violations.append(
                        Violation(
                            rule_id=self.rule_id,
                            severity=Severity.ERROR,
                            message=(
                                f"Feature '{feature.dir_name}' has status "
                                f"'{feature.status}' but is missing {file_name}.md"
                            ),
                            context={
                                "dir_name": feature.dir_name,
                                "status": feature.status,
                                "missing_file": file_name,
                            },
                            fix_hint=f"Create features/{feature.dir_name}/{file_name}.md",
                            suppress_if_creating=True,
                        )
                    )
        return violations


class R2_2_AdvancedFileForLowStatus:
    """Advanced file exists for a low status (e.g. implementation.md in Draft)."""

    rule_id = "R2.2"
    description = "Advanced file present for low status"
    wave = 1

    def check(self, graph: SpecGraph, specs_root: Path) -> list[Violation]:
        """Check that advanced files don't exist for low-status features.

        Args:
            graph: SpecGraph containing feature data.
            specs_root: Root directory of the .specs/ tree.

        Returns:
            List of violations for premature advanced files.
        """
        violations: list[Violation] = []
        for feature in graph.features:
            if feature.status != "Draft":
                continue

            if feature.files.get("implementation", False):
                violations.append(
                    Violation(
                        rule_id=self.rule_id,
                        severity=Severity.WARNING,
                        message=(
                            f"Feature '{feature.dir_name}' has status 'Draft' "
                            f"but implementation.md already exists"
                        ),
                        context={"dir_name": feature.dir_name, "status": "Draft"},
                        fix_hint="Update the feature status or remove implementation.md",
                        suppress_if_creating=True,
                    )
                )
        return violations


class R2_3_InvalidStatus:
    """Feature has an unrecognized status value."""

    rule_id = "R2.3"
    description = "Feature has an invalid status"
    wave = 1

    def check(self, graph: SpecGraph, specs_root: Path) -> list[Violation]:
        """Check that feature statuses are valid.

        Args:
            graph: SpecGraph containing feature data.
            specs_root: Root directory of the .specs/ tree.

        Returns:
            List of violations for invalid feature statuses.
        """
        violations: list[Violation] = []
        for feature in graph.features:
            if feature.status is None:
                continue

            if feature.status not in _VALID_STATUSES:
                violations.append(
                    Violation(
                        rule_id=self.rule_id,
                        severity=Severity.ERROR,
                        message=(
                            f"Feature '{feature.dir_name}' has invalid status "
                            f"'{feature.status}'. Valid: {', '.join(sorted(_VALID_STATUSES))}"
                        ),
                        context={
                            "dir_name": feature.dir_name,
                            "status": feature.status,
                            "valid_statuses": sorted(_VALID_STATUSES),
                        },
                        fix_hint="Update spec.md frontmatter to a valid status",
                        suppress_if_creating=False,
                    )
                )
        return violations
