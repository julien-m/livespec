# LiveSpec traceability anchors
# @spec(AC-003)
# @spec(AC-008)
# @spec(FR-003)
# @spec(FR-005)
# @spec(FR-007)
# @spec(FR-008)

"""Domain exceptions for the LiveSpec validator."""

from __future__ import annotations


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


# @spec FR-002: SDK dependency check error + install hint — .specs/features/002-layer-3-cli-surface/spec.md#fr-002  # noqa: E501
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
