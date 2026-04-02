"""R3 — Spec anchor rules: source file existence and anchor presence."""

from __future__ import annotations

import re
from pathlib import Path

from validator.coherence.graph_builder import SpecGraph
from validator.coherence.violation import Severity, Violation

_SPEC_ANCHOR_RE = re.compile(r"@spec\(?((?:FR|AC)-\d+)\)?")


class R3_1_SourceFileNotFound:
    """Check that every file path listed in implementation.md actually exists."""

    rule_id = "R3.1"
    description = "Source file referenced in implementation.md does not exist on disk"
    wave = 2
    specs_root: Path | None = None

    def check(self, graph: SpecGraph) -> list[Violation]:
        if self.specs_root is None:
            return []

        project_root = self.specs_root.parent
        violations: list[Violation] = []

        for feature in graph.features:
            if not feature.implementation_paths:
                continue

            for anchor_id, paths in feature.implementation_paths.items():
                for file_path in paths:
                    resolved = project_root / file_path
                    if not resolved.exists():
                        violations.append(
                            Violation(
                                rule_id=self.rule_id,
                                severity=Severity.WARNING,
                                message=(
                                    f"Source file '{file_path}' mapped to {anchor_id} "
                                    f"in feature '{feature.dir_name}' does not exist"
                                ),
                                context={
                                    "feature": feature.dir_name,
                                    "anchor": anchor_id,
                                    "path": file_path,
                                },
                                fix_hint=(
                                    f"Create '{file_path}' or update the mapping in "
                                    f".specs/features/{feature.dir_name}/implementation.md"
                                ),
                                suppress_if_creating=False,
                            )
                        )

        return violations


class R3_2_SpecAnchorMissing:
    """Check that each mapped source file contains the expected @spec anchor."""

    rule_id = "R3.2"
    description = "Source file does not contain the expected @spec(anchor) annotation"
    wave = 3
    specs_root: Path | None = None

    def check(self, graph: SpecGraph) -> list[Violation]:
        if self.specs_root is None:
            return []

        project_root = self.specs_root.parent
        violations: list[Violation] = []

        for feature in graph.features:
            if not feature.implementation_paths:
                continue

            for anchor_id, paths in feature.implementation_paths.items():
                for file_path in paths:
                    resolved = project_root / file_path
                    if not resolved.exists():
                        continue

                    try:
                        content = resolved.read_text()
                    except Exception:
                        continue

                    found_anchors = _SPEC_ANCHOR_RE.findall(content)
                    if anchor_id not in found_anchors:
                        violations.append(
                            Violation(
                                rule_id=self.rule_id,
                                severity=Severity.INFO,
                                message=(
                                    f"Source file '{file_path}' does not contain "
                                    f"@spec({anchor_id}) annotation"
                                ),
                                context={
                                    "feature": feature.dir_name,
                                    "anchor": anchor_id,
                                    "path": file_path,
                                },
                                fix_hint=(
                                    f"Add '@spec({anchor_id})' comment near the "
                                    f"relevant code in '{file_path}'"
                                ),
                                suppress_if_creating=False,
                            )
                        )

        return violations
