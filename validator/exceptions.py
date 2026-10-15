# LiveSpec traceability anchors
# @spec(AC-003)
# @spec(AC-008)
# @spec(FR-003)
# @spec(FR-005)
# @spec(FR-007)
# @spec(FR-008)

"""Domain exceptions for the LiveSpec validator."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path


class SpecsRootNotFoundError(Exception):
    """Raised when the .specs/ directory cannot be found.

    Args:
        search_path: The path that was searched from.
    """

    def __init__(self, search_path: str) -> None:
        super().__init__(f".specs/ directory not found from {search_path}")
        self.search_path = search_path


class PlanReviewError(Exception):
    """Raised when an LLM plan review fails for a feature.

    Args:
        feature_name: The feature directory name.
        reason: Description of the failure.
    """

    def __init__(self, feature_name: str, reason: str) -> None:
        super().__init__(f"Plan review failed for {feature_name}: {reason}")
        self.feature_name = feature_name
        self.reason = reason


class AssertionExtractionError(Exception):
    """Raised when LLM assertion extraction fails for a document.

    Args:
        document: Source document path.
        reason: Description of the failure.
    """

    def __init__(self, document: str, reason: str) -> None:
        super().__init__(f"Assertion extraction failed for {document}: {reason}")
        self.document = document
        self.reason = reason


# @spec FR-009: Domain exception for spec review
# .specs/features/001-auto-llm-review/spec.md#fr-009
class SpecReviewError(Exception):
    """Raised when an LLM spec review fails for a feature.

    Args:
        feature_name: The feature directory name.
        reason: Description of the failure.
    """

    def __init__(self, feature_name: str, reason: str) -> None:
        super().__init__(f"Spec review failed for {feature_name}: {reason}")
        self.feature_name = feature_name
        self.reason = reason


class ContradictionComparisonError(Exception):
    """Raised when LLM contradiction comparison fails.

    Args:
        doc_a: First document path.
        doc_b: Second document path.
        reason: Description of the failure.
    """

    def __init__(self, doc_a: str, doc_b: str, reason: str) -> None:
        super().__init__(f"Comparison failed for {doc_a} x {doc_b}: {reason}")
        self.doc_a = doc_a
        self.doc_b = doc_b
        self.reason = reason


# @spec FR-002: SDK dependency check error + install hint
#   — .specs/features/002-layer-3-cli-surface/spec.md#fr-002
class SdkDependencyError(Exception):
    """Raised when claude-agent-sdk is not importable.

    Args:
        install_hint: pip install command to fix the issue.
    """

    INSTALL_HINT = "pip install -e .[integration]"

    def __init__(self) -> None:
        super().__init__(
            f"claude-agent-sdk is required for --sdk-isolated.\n"
            f"Install it with: {self.INSTALL_HINT}"
        )
        self.install_hint: str = self.INSTALL_HINT


# @spec FR-007 — TaxonomyLoadError — .specs/features/006-taxonomy-testing-infra/spec.md#fr-007
class TaxonomyLoadError(Exception):
    """Raised when the UI behavioral taxonomy file is missing or unparseable.

    Args:
        path: The taxonomy file path that was searched.
        reason: Optional parse failure description.
    """

    def __init__(self, path: str, reason: str | None = None) -> None:
        msg = f"Taxonomy not found at {path}"
        if reason:
            msg += f": {reason}"
        super().__init__(msg)
        self.path = path
        self.reason = reason


# @spec FR-004: Subprocess failure error — .specs/features/002-layer-3-cli-surface/spec.md#fr-004
# @spec FR-003: ExpectationsMissing
#   — .specs/features/039-command-expectations-and-verify-output/spec.md#fr-003
class ExpectationsMissing(Exception):
    """Raised when no expectations file can be found for a command.

    Args:
        command: The command name that was looked up.
        searched_paths: The paths that were checked in lookup order.
    """

    def __init__(self, command: str, searched_paths: list[str]) -> None:
        paths_str = ", ".join(searched_paths)
        super().__init__(f"No expectations file for {command!r} (searched: {paths_str})")
        self.command = command
        self.searched_paths = searched_paths


# @spec FR-003: ExpectationsInvalid
#   — .specs/features/039-command-expectations-and-verify-output/spec.md#fr-003
class ExpectationsInvalid(Exception):
    """Raised when an expectations file fails schema validation.

    Args:
        path: Path to the offending file.
        reason: Description of the validation failure.
    """

    def __init__(self, path: str, reason: str) -> None:
        super().__init__(f"Invalid expectations file {path}: {reason}")
        self.path = path
        self.reason = reason


# @spec FR-008: OverrideMalformed
#   — .specs/features/039-command-expectations-and-verify-output/spec.md#fr-008
class OverrideMalformed(Exception):
    """Raised when a project override is malformed.

    The verifier MUST NOT silently fall back to the builtin — it blocks
    (exit 2) so the operator sees the override problem.

    Args:
        path: Path to the malformed override.
        reason: Description of the failure.
    """

    def __init__(self, path: str, reason: str) -> None:
        super().__init__(f"Override malformed at {path}: {reason}")
        self.path = path
        self.reason = reason


# @spec FR-005: ArtifactMalformed
#   — .specs/features/039-command-expectations-and-verify-output/spec.md#fr-005
class ArtifactMalformed(Exception):
    """Raised when a RunArtifact JSON file cannot be parsed.

    Mapped to outcome=blocked by the verifier (EC-007).

    Args:
        path: Path to the malformed artifact.
        reason: Description of the failure (typically a JSONDecodeError).
    """

    def __init__(self, path: str, reason: str) -> None:
        super().__init__(f"Malformed run artifact at {path}: {reason}")
        self.path = path
        self.reason = reason


class SdkTestRunError(Exception):
    """Raised when the pytest subprocess fails to start.

    Args:
        command: The subprocess command that failed.
        reason: Description of the failure.
    """

    def __init__(self, command: list[str], reason: str) -> None:
        super().__init__(f"pytest subprocess failed ({reason}): {' '.join(command)}")
        self.command = command
        self.reason = reason


class FeatureResolutionError(Exception):
    """Raised when a ``--feature`` value does not name exactly one feature directory.

    Args:
        value: The ``--feature`` argument as typed by the user.
        matches: Feature directory names that matched (zero or several).
    """

    # @spec AC-002: Unique feature resolution
    # — .specs/features/035-unified-cli-surface/spec.md#ac-002

    def __init__(self, value: str, matches: list[str]) -> None:
        found = ", ".join(matches) if matches else "none"
        super().__init__(
            f"--feature {value!r} must match exactly one .specs/features/ directory "
            f"(matched: {found}). Pass the number (e.g. 035) or the full directory name."
        )
        self.value = value
        self.matches = matches


class DriverTestSelectionError(Exception):
    """Raised when a capability cannot run a selected subset of tests.

    Args:
        driver_name: Driver whose capability lacks ``test_selection: append``.
        capability: Capability name that was asked to run selected tests.
    """

    # @spec AC-002: Explicit refusal without test_selection
    # — .specs/features/035-unified-cli-surface/spec.md#ac-002

    def __init__(self, driver_name: str, capability: str) -> None:
        super().__init__(
            f"driver {driver_name!r} {capability} capability does not declare "
            "test_selection: append, so it cannot run feature-scoped tests. "
            "Add `test_selection: append` to the capability or run without --feature."
        )
        self.driver_name = driver_name
        self.capability = capability


class XcuitestTargetUnresolvedError(Exception):
    """Raised when no single XCUITest target directory receives generated journeys.

    Args:
        surface: Journey surface (``ios`` or ``watchos``).
        candidates: Matching ``*UITests`` directory names (zero or several).
    """

    # @spec FR-007: Explicit refusal instead of a hardcoded destination
    # — .specs/features/056-executable-user-journeys/spec.md#fr-007

    def __init__(self, surface: str, candidates: list[str]) -> None:
        found = ", ".join(candidates) if candidates else "none"
        super().__init__(
            f"cannot resolve the {surface} XCUITest target directory (candidates: {found}); "
            f"keep exactly one top-level *UITests directory for {surface} or declare testDir "
            "on the matching runner: xcuitest surface in .specs/surfaces.yaml"
        )
        self.surface = surface
        self.candidates = candidates


AIRESOURCES_FIX_SENTENCE = (
    "Run ./setup.sh from your ai-ressources clone, "
    "or export AIRESOURCES=<absolute path of the clone>."
)
"""Actionable fix appended to every ai-ressources resolution error message."""


# @spec FR-002: Dedicated error and message
#   .specs/features/085-localiser-ai-ressources-sans-chemin-en-dur/spec.md#fr-002
class AiResourcesResolutionError(ValueError):
    """Raised when no ai-ressources root resolves for a project.

    It subclasses ``ValueError`` so existing ``ValueError`` boundaries (for
    example ``livespec conventions compile``) surface it unchanged.

    Args:
        project_root: Absolute project root that was consulted, or ``None``
            when only the environment could be read.
        rejected: Recorded paths found but rejected, as ``(absolute path,
            source file)`` pairs in resolution order.
    """

    def __init__(self, project_root: Path | None, rejected: Sequence[tuple[Path, str]]) -> None:
        super().__init__(_resolution_message(project_root, rejected))
        self.project_root = project_root
        self.rejected: tuple[tuple[Path, str], ...] = tuple(rejected)


def _resolution_message(project_root: Path | None, rejected: Sequence[tuple[Path, str]]) -> str:
    # One line, so the message fits a JSON field, a violation and an `ERROR:` line.
    if project_root is None:
        return (
            f"ai-ressources root not resolved: AIRESOURCES is not set. {AIRESOURCES_FIX_SENTENCE}"
        )
    if rejected:
        listed = "; ".join(f"{path} (from {source})" for path, source in rejected)
        detail = f"rejected recorded paths: {listed}"
    else:
        detail = "no path recorded in .conventions/manifest.yaml or .conventions/index.md"
    return (
        f"ai-ressources root not resolved for project {project_root}: "
        f"AIRESOURCES is not set; {detail}. {AIRESOURCES_FIX_SENTENCE}"
    )
