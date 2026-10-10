"""Validate native semantic and test operation selection before project access."""

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SemanticOptions:
    """Parsed values for semantic dispatch; construction performs no validation or I/O.

    Attributes:
        clarification: Inspection or accepted-answer application was requested.
        prepare: Review purpose requested, or None when absent.
        ingest: Raw review bundle path, or None when absent; retained without reading it.
        progression: Requested destination, or None when absent.
        pre_impl: Analyze mode is active.
        structural_only: Analyze should provide reference diagnostics only.
        state_files: Legacy state-file validation or migration is active.
        kind: Ingestion purpose; the inert default is plan.
        budget: Explicit review character budget, or None for the configured default.
    """

    clarification: bool
    prepare: str | None
    ingest: Path | None
    progression: str | None
    pre_impl: bool
    structural_only: bool
    state_files: bool
    kind: str
    budget: int | None


def check_semantic_options(options: SemanticOptions, legacy_flags: Mapping[str, bool]) -> None:
    """Reject conflicting actions and unconsumed modifiers before dispatch.

    Args:
        options: Parsed semantic and competing early-mode values.
        legacy_flags: Option labels mapped to whether their non-default behavior is requested.
    Returns:
        None when the operation selection is supported.
    Raises:
        ValueError: The selection conflicts or a modifier has no consuming operation.
    Side effects:
        None; inputs and referenced paths are neither changed nor read.
    """
    active = sum(
        (
            options.clarification,
            options.prepare is not None,
            options.ingest is not None,
            options.progression is not None,
        )
    )
    _check_analysis_conflicts(options, active)
    if options.progression is not None and (
        options.prepare is not None or options.ingest is not None
    ):
        raise ValueError(
            "--progression cannot be combined with --prepare-review or --ingest-review"
        )
    if active > 1:
        raise ValueError(
            "select one semantic operation: clarification, prepare, ingest or progression"
        )
    if active and options.state_files:
        raise ValueError("semantic operations cannot be combined with --state-files")
    conflicting = [flag for flag, enabled in legacy_flags.items() if enabled]
    if active and conflicting:
        raise ValueError("semantic operations do not support " + ", ".join(conflicting))
    if options.ingest is None and options.kind != "plan":
        raise ValueError("--review-kind requires --ingest-review")
    if options.budget is not None and not (active or options.pre_impl):
        raise ValueError("--review-max-chars requires a semantic operation or --pre-impl")
    _check_semantic_values(options)


def _check_semantic_values(options: SemanticOptions) -> None:
    """Reject present-but-empty and unknown operations before truth-based dispatch."""
    if options.prepare is not None and options.prepare not in ("spec", "plan", "acceptance"):
        raise ValueError("--prepare-review must be spec, plan or acceptance")
    if options.ingest is not None and options.kind not in ("spec", "plan", "acceptance"):
        raise ValueError("--review-kind must be spec, plan or acceptance")
    if options.progression is not None and options.progression not in (
        "plan",
        "implement",
        "test",
        "complete",
        "clarify",
        "analyze",
    ):
        raise ValueError("unknown_progression_destination:" + options.progression)


def _check_analysis_conflicts(options: SemanticOptions, active: int) -> None:
    """Preserve established Analyze diagnostics and its legacy read-only fix/smart semantics."""
    if options.structural_only and not options.pre_impl:
        raise ValueError("--structural-only requires --pre-impl")
    if options.structural_only and (options.state_files or active):
        raise ValueError(
            "--structural-only cannot be combined with --state-files, --clarify, "
            "--clarification-answer, --prepare-review, --ingest-review or --progression"
        )
    if options.pre_impl and active:
        raise ValueError(
            "--pre-impl cannot be combined with --clarify, --clarification-answer, "
            "--prepare-review, --ingest-review or --progression"
        )


def check_execution_options(
    *,
    feature: str | None,
    command: str | None,
    mapping: Path | None,
    prepare: bool,
    ingest: Path | None,
    adapter: str,
    mutation: bool,
    no_coverage: bool,
    debug: bool,
) -> bool:
    """Validate native test selection before resolving project inputs.

    Args:
        feature: Selected feature slug; mandatory for native operations.
        command: Execution argv text, or None when absent.
        mapping: Acceptance mapping path, or None when absent.
        prepare: Mapping review preparation was requested.
        ingest: Raw mapping-review bundle path, or None when absent.
        adapter: Execution report adapter; only execution consumes non-default values.
        mutation: Legacy driver mutation was requested.
        no_coverage: Legacy driver coverage suppression was requested.
        debug: Legacy driver tracebacks were requested.
    Returns:
        True for a complete native request, False for an unchanged legacy request.
    Raises:
        ValueError: Native inputs are incomplete, conflicting or contain unused modifiers.
    Side effects:
        None; supplied values and referenced files remain untouched.
    """
    active = sum((command is not None, prepare, ingest is not None))
    native = bool(active or mapping is not None or adapter != "junit")
    if not native:
        return False
    if active != 1:
        raise ValueError("select exactly one native test operation: prepare, ingest or execution")
    if mapping is None or not feature or not feature.strip():
        raise ValueError("native test operations require --feature and --acceptance-mapping")
    if command is not None and not command.strip():
        raise ValueError("--execution-command must not be empty")
    if mutation or no_coverage or debug:
        raise ValueError(
            "native test operations do not support --mutation, --no-coverage or --debug"
        )
    if command is None and adapter != "junit":
        raise ValueError("--report-adapter requires --execution-command")
    return True
