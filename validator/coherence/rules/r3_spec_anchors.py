"""R3 — Spec anchor rules: source file existence and anchor presence."""

from __future__ import annotations

import logging
import re
from pathlib import Path

from validator.coherence.graph_builder import SpecGraph
from validator.coherence.violation import Severity, Violation

_SPEC_ANCHOR_RE = re.compile(r"@spec\(?((?:FR|AC)-\d+)\)?")
_LINE_SUFFIX_RE = re.compile(r"^(.+\.[A-Za-z0-9]+):\d+$")


class R3_1_SourceFileNotFound:
    """Check that every file path listed in implementation.md actually exists."""

    rule_id = "R3.1"
    description = "Source file referenced in implementation.md does not exist on disk"
    wave = 2

    def check(self, graph: SpecGraph, specs_root: Path) -> list[Violation]:
        """Check that implementation file paths exist on disk.

        Args:
            graph: SpecGraph containing feature implementation mappings.
            specs_root: Root directory of the .specs/ tree.

        Returns:
            List of violations for missing source files.
        """
        project_root = specs_root.parent
        violations: list[Violation] = []

        for feature in graph.features:
            if not feature.implementation_paths:
                continue

            for anchor_id, paths in feature.implementation_paths.items():
                for file_path in paths:
                    if not _mapped_path_exists(project_root, file_path):
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

    def check(self, graph: SpecGraph, specs_root: Path) -> list[Violation]:
        """Check that source files contain expected @spec anchors.

        Args:
            graph: SpecGraph containing feature implementation mappings.
            specs_root: Root directory of the .specs/ tree.

        Returns:
            List of violations for missing @spec annotations.
        """
        project_root = specs_root.parent
        violations: list[Violation] = []

        for feature in graph.features:
            if not feature.implementation_paths:
                continue

            for anchor_id, paths in feature.implementation_paths.items():
                for file_path in paths:
                    resolved = project_root / _path_part(file_path)
                    if not resolved.is_file():
                        continue

                    try:
                        content = resolved.read_text()
                    except (OSError, UnicodeDecodeError) as exc:  # Narrow: file read errors only
                        logging.warning("Failed to read %s: %s", resolved, exc)
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


def _path_part(raw_path: str) -> str:
    """Strip test selectors and Markdown line suffixes from a mapped path."""
    path_part = raw_path.split("::", 1)[0]
    match = _LINE_SUFFIX_RE.match(path_part)
    if match:
        return match.group(1)
    return path_part


def _mapped_path_exists(project_root: Path, raw_path: str) -> bool:
    """Return whether a mapped path exists, supporting repo-relative globs."""
    path_part = _path_part(raw_path)
    if any(char in path_part for char in "*?["):
        return any(project_root.glob(path_part))
    return (project_root / path_part).exists()
