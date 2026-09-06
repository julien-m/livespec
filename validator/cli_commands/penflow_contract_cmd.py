# LiveSpec traceability anchors
# @spec(FR-002)
# @spec(FR-009)
# @spec(FR-010)

"""CLI surface for root Penflow UI contract workspaces."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from yaml import YAMLError

from validator.penflow_contract import (
    PenflowContractStatus,
    PenflowTarget,
    bootstrap_penflow_workspace,
    get_penflow_contract_status,
)
from validator.penflow_verification import VerificationProfile

penflow_contract_app = typer.Typer(
    name="penflow-contract",
    help="Inspect and bootstrap the root penflow/ UI contract workspace.",
    no_args_is_help=True,
)


def register(app: typer.Typer) -> None:
    """Register the ``penflow-contract`` command group.

    Args:
        app: Top-level Typer app mutated with the Penflow command group.
    """
    app.add_typer(penflow_contract_app, name="penflow-contract")


def _verdict_from_status(status: PenflowContractStatus) -> str:
    """Return the observable Penflow contract verdict for CLI consumers."""
    # @spec FR-001, FR-003: Readiness never certifies
    # .specs/features/077-penflow-cumulative-verdict-consumer/spec.md#fr-001
    if status.verification is not None:
        return "PASS" if status.certified else status.verification.status
    if status.state == "absent":
        return "ABSENT"
    if status.state == "incomplete" or status.runtime_comparison in {"BLOCKED", "FAIL"}:
        return "BLOCKED"
    return "READY"


@penflow_contract_app.command("status")
def status_command(
    project: Annotated[
        Path,
        typer.Option("--project", help="Project root containing penflow/."),
    ] = Path("."),
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Emit machine-readable JSON."),
    ] = False,
    require_actual: Annotated[
        bool,
        typer.Option(
            "--require-actual",
            help="Alias for implementation certification with an independent runner manifest.",
        ),
    ] = False,
    require_design_registry: Annotated[
        bool,
        typer.Option(
            "--require-design-registry",
            help="Require .specs/design ui.pen, mockups, index, changelog, and baselines.",
        ),
    ] = False,
    require_mockup_validation: Annotated[
        bool,
        typer.Option(
            "--require-mockup-validation",
            help="Require partial Mockup Factory evidence without requesting C51 certification.",
        ),
    ] = False,
    feature: Annotated[
        str | None,
        typer.Option(
            "--feature", help="Feature slug required for certification and registry scope."
        ),
    ] = None,
    target: Annotated[
        PenflowTarget | None,
        typer.Option(
            "--target",
            help="Optional UI target; use web-desktop to reject mobile-sized desktop mockups.",
        ),
    ] = None,
    required_profile: Annotated[
        VerificationProfile | None,
        typer.Option(
            "--required-profile", help="Require current design or implementation certification."
        ),
    ] = None,
    build_manifest: Annotated[
        Path | None,
        typer.Option(
            "--build-manifest", help="Independent runner build manifest for implementation."
        ),
    ] = None,
) -> None:
    """Print root Penflow workspace status.

    Args:
        project: Project root to inspect.
        json_output: Emit parseable JSON instead of human-readable text.
        require_actual: Require implementation certification through the compatibility alias.
        require_design_registry: Treat missing project-level design registry
            artifacts as blocking.
        require_mockup_validation: Treat missing Mockup Factory evidence as
            blocking.
        feature: Caller feature required for certification; optional for registry inspection.
        target: Optional UI target used for mockup quality checks.
        required_profile: Required Penflow certification stage; inspection otherwise.
        build_manifest: Independent build identity forwarded to Penflow for implementation.

    Side effects:
        Writes status to stdout; success exits 0, noncertifying closure exits 1.
    """
    status = get_penflow_contract_status(
        project.resolve(),
        require_actual=require_actual,
        require_design_registry=require_design_registry,
        require_mockup_validation=require_mockup_validation,
        feature_slug=feature,
        target=target,
        required_profile=required_profile,
        build_manifest=build_manifest,
    )
    verdict = _verdict_from_status(status)
    if json_output:
        payload = status.to_dict()
        payload["verdict"] = verdict
        typer.echo(json.dumps(payload, indent=2))
    else:
        typer.echo(f"Penflow contract: {status.state}")
        typer.echo(f"Runtime comparison: {status.runtime_comparison}")
        typer.echo(f"Runtime reason: {status.runtime_reason}")
        typer.echo(f"Certified: {str(status.certified).lower()}")
        if status.verification is not None:
            typer.echo(f"Verification: {status.verification.reason}")
        if status.compare_status is not None:
            typer.echo(f"Compare report status: {status.compare_status}")
        if status.compare_issue_count is not None:
            typer.echo(f"Compare report issues: {status.compare_issue_count}")
        typer.echo(f"Workspace: {status.workspace}")
        typer.echo(f"Present: {', '.join(status.present) or 'none'}")
        typer.echo(f"Missing: {', '.join(status.missing) or 'none'}")
        if status.design_registry_required:
            typer.echo(
                f"Design registry missing: {', '.join(status.design_registry_missing) or 'none'}"
            )
        if status.mockup_validation_required:
            typer.echo(
                "Mockup validation missing: "
                f"{', '.join(status.mockup_validation_missing) or 'none'}"
            )
            typer.echo(f"Mockup validation status: {status.mockup_validation_status or 'none'}")
        typer.echo(f"Flows: {status.flow_count} · Screens: {status.screen_count}")
        if status.parse_error:
            typer.echo(f"Semantic tree parse warning: {status.parse_error}", err=True)
        typer.echo(f"Penflow Contract Verdict: {verdict}")
    raise typer.Exit(0 if verdict in {"PASS", "READY", "ABSENT"} else 1)


@penflow_contract_app.command("bootstrap")
def bootstrap_command(
    project: Annotated[
        Path,
        typer.Option("--project", help="LiveSpec project root receiving root penflow/."),
    ] = Path("."),
    source: Annotated[
        Path | None,
        typer.Option(
            "--source",
            help="Explicit Brainstorm penflow/ directory to import into the LiveSpec project.",
        ),
    ] = None,
    source_project: Annotated[
        Path | None,
        typer.Option(
            "--source-project",
            help="Exact Brainstorm consumer root for authenticated ancestry import",
        ),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Emit machine-readable JSON."),
    ] = False,
) -> None:
    """Copy a Brainstorm ``penflow/`` directory to root ``penflow/`` when absent.

    Args:
        project: LiveSpec project root receiving root ``penflow/``.
        source: Optional explicit Brainstorm ``penflow/`` source directory.
        json_output: Emit parseable JSON instead of human-readable text.

    Side effects:
        May copy a Penflow workspace and writes the result to stdout.
    """
    try:
        result = bootstrap_penflow_workspace(
            project.resolve(),
            source_dir=source if source is not None else None,
            source_project_root=source_project,
        )
    except (OSError, ValueError, RuntimeError, YAMLError) as exc:
        typer.echo(
            json.dumps({"status": "BLOCKED", "certified": False, "reason": str(exc)})
            if json_output
            else f"BLOCKED: {exc}"
        )
        raise typer.Exit(1) from exc
    if json_output:
        typer.echo(json.dumps(result.to_dict(), indent=2))
    else:
        typer.echo(f"Penflow bootstrap: {result.reason}")
        typer.echo(f"Source: {result.source}")
        typer.echo(f"Destination: {result.destination}")
        typer.echo(f"Status: {result.status.state}")
    raise typer.Exit(0)


# Export the command group and registrar for the unified CLI loader.
__all__ = ["penflow_contract_app", "register"]


@penflow_contract_app.command("review-snapshot")
def review_snapshot_command(
    feature: Annotated[
        str, typer.Option("--feature", help="Selected feature reviewed by this workflow")
    ],
    project: Annotated[Path, typer.Option("--project", help="Consumer project root")] = Path("."),
    json_output: Annotated[
        bool, typer.Option("--json", help="Emit structured snapshot identity")
    ] = False,
) -> None:
    """Archive source and mapping inputs before the real plan reviewer runs."""
    from validator.penflow_review_snapshot import create_review_snapshot

    try:
        result = create_review_snapshot(project, feature)
    except (OSError, ValueError, RuntimeError, YAMLError) as exc:
        if json_output:
            typer.echo(json.dumps({"status": "BLOCKED", "certified": False, "reason": str(exc)}))
        else:
            typer.echo(f"BLOCKED: {exc}", err=True)
        raise typer.Exit(1) from exc
    typer.echo(
        json.dumps(result, indent=2)
        if json_output
        else f"Review snapshot: {result['snapshot']['path']}"
    )


@penflow_contract_app.command("review-result")
def review_result_command(
    snapshot: Annotated[Path, typer.Option("--snapshot", help="Immutable workflow snapshot")],
    output: Annotated[Path, typer.Option("--output", help="Actual raw reviewer JSON output")],
    project: Annotated[Path, typer.Option("--project", help="Consumer project root")] = Path("."),
    json_output: Annotated[
        bool, typer.Option("--json", help="Emit structured bound result identity")
    ] = False,
) -> None:
    """Package the actual reviewer response for the existing approval transition."""
    from validator.penflow_review_result import package_review_result

    try:
        result = package_review_result(project, snapshot, output)
    except (OSError, ValueError, RuntimeError, YAMLError) as exc:
        if json_output:
            typer.echo(json.dumps({"status": "BLOCKED", "certified": False, "reason": str(exc)}))
        else:
            typer.echo(f"BLOCKED: {exc}", err=True)
        raise typer.Exit(1) from exc
    typer.echo(
        json.dumps(result, indent=2)
        if json_output
        else f"Review result: {result['result']['path']} ({result['verdict']}, uncertified)"
    )


@penflow_contract_app.command("policy-source")
def policy_source_command(
    workflow: Annotated[
        Path,
        typer.Option(
            "--workflow", help="Actual producing workflow with declared verification modes"
        ),
    ],
    project: Annotated[Path, typer.Option("--project", help="Consumer project root")] = Path("."),
    json_output: Annotated[
        bool, typer.Option("--json", help="Emit generated source reference")
    ] = False,
) -> None:
    """Archive actual workflow decisions for automatic use by the plan review."""
    from validator.penflow_policy_source import generate_policy_source

    try:
        result = generate_policy_source(project, workflow)
    except (OSError, ValueError, RuntimeError, YAMLError) as exc:
        typer.echo(
            json.dumps({"status": "BLOCKED", "certified": False, "reason": str(exc)})
            if json_output
            else f"BLOCKED: {exc}"
        )
        raise typer.Exit(1) from exc
    typer.echo(
        json.dumps({"source": result, "certified": False})
        if json_output
        else f"Policy source: {result['path']}"
    )
