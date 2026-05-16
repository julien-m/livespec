"""CLI entry point for LiveSpec validator."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import TYPE_CHECKING, Any

import typer

from .cli_commands import register_unified_commands
from .cli_commands.run_cmd import run_app
from .cli_commands.verify_output_cmd import register as register_verify_output
from .commit_context import commit_context_app
from .config import load_config
from .drivers.cli import driver_app
from .drivers.test_config_cli import init_app
from .engine import validate_all
from .exceptions import SpecsRootNotFoundError
from .fixer import fix_all
from .git_ops import git_app
from .hooks_cli import hooks_app, integrations_app
from .pipeline import pipeline_app
from .reporter import report, report_excluded, report_score_only
from .specs_utils import find_specs_root

if TYPE_CHECKING:
    from .sdk_test_runner import SdkTestResult

app = typer.Typer(name="livespec", help="LiveSpec structural validator")
app.add_typer(pipeline_app, name="pipeline")
app.add_typer(git_app, name="git")
app.add_typer(commit_context_app, name="commit-context")
app.add_typer(driver_app, name="spec.driver")
# @spec FR-001 (feature 023): backward-compat alias for the old `spec-driver` name.
app.add_typer(driver_app, name="spec-driver", hidden=True)
# @spec FR-005 (feature 026): livespec init test-config — used by /spec.init Phase C.
app.add_typer(init_app, name="init")
# @spec FR-001..005 (feature 035): unified short-form CLI surface.
register_unified_commands(app)
# @spec FR-006, FR-007 (feature 039): verify-output + run wrap/record.
register_verify_output(app)
app.add_typer(run_app, name="run")
# Feature: integration-markdown-pattern — hook resolution runtime CLI + L0 diagnostic.
app.add_typer(hooks_app, name="hooks")
app.add_typer(integrations_app, name="integrations")


def _find_specs_root(start: Path | None = None) -> Path:
    """Find the .specs/ directory starting from the given path or cwd.

    Args:
        start: Starting path to search from, or None for cwd.

    Returns:
        Path to the .specs/ directory.

    Raises:
        SpecsRootNotFoundError: If .specs/ cannot be found.
    """
    return find_specs_root(start)


def _require_specs_root(start: Path | None = None) -> Path:
    """Find .specs/ or exit with a user-friendly error.

    CLI boundary wrapper around _find_specs_root. Converts domain
    exceptions into typer.Exit for the command layer.

    Args:
        start: Starting path to search from, or None for cwd.

    Returns:
        Path to the .specs/ directory.

    Raises:
        typer.Exit: If .specs/ cannot be found.
    """
    try:
        return _find_specs_root(start)
    except SpecsRootNotFoundError:
        typer.echo("Error: .specs/ directory not found", err=True)
        raise typer.Exit(1)  # noqa: B904 — intentional exit, not re-raise


def _resolve_feature_filter(
    target: Path | None,
    specs_root: Path,
) -> str | None:
    """Resolve a path to a feature dir_name for plan-review scoping.

    Args:
        target: User-provided path (file or directory), or None.
        specs_root: Root of the .specs/ tree.

    Returns:
        Feature dir_name if path resolves to a feature, None otherwise.
    """
    if target is None:
        return None
    try:
        rel = target.resolve().relative_to(
            (specs_root / "features").resolve(),
        )
    except ValueError:
        return None
    return rel.parts[0] if rel.parts else None


# @spec FR-006: Feature slug resolution — .specs/features/002-layer-3-cli-surface/spec.md#fr-006
def _resolve_feature_slug(path: Path | None, specs_root: Path) -> str | None:
    """Derive a pytest -k slug from an optional feature directory path.

    Reuses _resolve_feature_filter() for path validation, then converts
    hyphens to underscores for the pytest -k filter.

    Args:
        path: User-provided path (file or directory), or None.
        specs_root: Root of the .specs/ tree.

    Returns:
        Underscore-normalized slug string, or None (fall back to full suite).
    """
    if path is None:
        return None
    raw = _resolve_feature_filter(path, specs_root)
    if raw is None:
        typer.echo(
            f"Warning: {path} does not match a .specs/features/ directory"
            " — running full level_3b suite",
            err=True,
        )
        return None
    return raw.replace("-", "_")


def _display_review_findings(
    reviews: list[Any],
    errors: list[str],
    review_type: str,
    sem_config: object,
) -> bool:
    """Display review findings to stderr and return blocking status.

    Args:
        reviews: List of review entry objects (PlanReviewEntry or SpecReviewEntry).
        errors: List of error messages.
        review_type: "Spec" or "Plan" for display labels.
        sem_config: Semantic config with review_confidence_threshold.

    Returns:
        True if any blocking finding or error exists.
    """
    has_blocking = False
    for entry in reviews:
        name = entry.feature_name
        model = entry.result.reviewer_model
        typer.echo(
            f"\n{review_type} Review: {name} ({model})",
            err=True,
        )
        for finding in entry.result.findings:
            marker = finding.severity.value
            typer.echo(
                f"  [{marker}] {finding.category}: {finding.description}",
                err=True,
            )
            if finding.suggestion:
                typer.echo(f"    -> {finding.suggestion}", err=True)
            if finding.severity.value == "ERROR":
                has_blocking = True

        # Display metrics (complexity for plan, spec_metrics for spec)
        metrics = getattr(entry.result, "complexity", None) or getattr(
            entry.result, "spec_metrics", {}
        )
        metric_parts = [
            f"{v} {k.replace('_count', '').replace('_', ' ')}" for k, v in metrics.items()
        ]
        typer.echo(
            f"  Confidence: {entry.result.confidence}/5 | "
            f"Findings: {len(entry.result.findings)} | "
            f"Metrics: {', '.join(metric_parts)}",
            err=True,
        )

        threshold = getattr(sem_config, "review_confidence_threshold", 3.0)
        if (
            entry.result.confidence < threshold
            and len(entry.result.findings) == 0
            and sum(metrics.values()) > 5
        ):
            typer.echo(
                "  Warning: Review suspiciously empty for this complexity.",
                err=True,
            )

    for error in errors:
        typer.echo(f"  Error: {error}", err=True)

    if errors:
        has_blocking = True

    total = sum(len(e.result.findings) for e in reviews)
    count = len(reviews)
    typer.echo(
        f"\n{total} finding(s) across {count} review(s).",
        err=True,
    )
    return has_blocking


def _output_review_json(reviews: list[Any], errors: list[str]) -> None:
    """Output review findings as JSON to stdout.

    Args:
        reviews: List of review entry objects.
        errors: List of error messages.
    """
    import json as json_mod

    data = {
        "reviews": [
            {
                "feature": e.feature_name,
                "model": e.result.reviewer_model,
                "confidence": e.result.confidence,
                "findings": [
                    {
                        "category": f.category,
                        "severity": f.severity.value,
                        "description": f.description,
                        "suggestion": f.suggestion,
                    }
                    for f in e.result.findings
                ],
            }
            for e in reviews
        ],
        "errors": errors,
    }
    typer.echo(json_mod.dumps(data, indent=2))


def _output_sdk_result_json(result: SdkTestResult) -> None:
    """Output SDK test result as JSON to stdout.

    Schema: {"passed": N, "failed": N, "skipped": N, "total": N, "exit_code": N}
    raw_output is NOT included — it is forwarded to stderr during streaming.

    Args:
        result: SdkTestResult from the test runner.
    """
    import json as json_mod

    data = {
        "passed": result.passed,
        "failed": result.failed,
        "skipped": result.skipped,
        "total": result.total,
        "exit_code": result.exit_code,
    }
    typer.echo(json_mod.dumps(data))


@app.command()
def validate(
    path: str | None = typer.Argument(None, help="File or directory to validate"),
    staged: bool = typer.Option(False, "--staged", help="Validate git staged files only"),
    output_format: str = typer.Option(
        "compact",
        "--format",
        "-f",
        help="Output format: compact, full, json",
    ),
    warn_only: bool = typer.Option(False, "--warn-only", help="Don't exit with error code"),
    score_only: bool = typer.Option(False, "--score-only", help="Show scores only"),
    fix: bool = typer.Option(False, "--fix", help="Apply Pass 1 mechanical fixes"),
    smart: bool = typer.Option(
        False,
        "--smart",
        help="Apply Pass 2 Claude SDK fixes (not yet implemented)",
    ),
    auto: bool = typer.Option(False, "--auto", help="Skip confirmation prompts"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview fixes without modifying files"),
    list_excluded: bool = typer.Option(False, "--list-excluded", help="Show excluded files"),
    coherence: bool = typer.Option(False, "--coherence", help="Run Layer 2 coherence validation"),
    coherence_only: bool = typer.Option(
        False,
        "--coherence-only",
        help="Run only Layer 2 (skip Layer 1)",
    ),
    rules: str | None = typer.Option(None, "--rules", help="Specific rules to run (e.g., R1,R2)"),
    wave_num: int | None = typer.Option(None, "--wave", help="Only run rules up to this wave"),
    ignore_rules: str | None = typer.Option(
        None,
        "--ignore",
        help="Rules to ignore (e.g., R3.2,R5.1)",
    ),
    strict: bool = typer.Option(False, "--strict", help="Block on coherence errors"),
    no_suppress: bool = typer.Option(False, "--no-suppress", help="Disable suppress_if_creating"),
    semantic: bool = typer.Option(False, "--semantic", help="Run Layer 4 semantic validation"),
    scorecard: bool = typer.Option(False, "--scorecard", help="Run scorecard only"),
    contradiction_only: bool = typer.Option(
        False,
        "--contradiction-only",
        help="Run contradiction detection only",
    ),
    reindex: bool = typer.Option(False, "--reindex", help="Reindex embeddings"),
    mutate: bool = typer.Option(False, "--mutate", help="Run mutation testing"),
    experimental_multi_model: bool = typer.Option(
        False,
        "--experimental-multi-model",
        help="Enable multi-model consensus",
    ),
    plan_review: bool = typer.Option(
        False,
        "--plan-review",
        "--review-plan",
        "-r",
        help="Run LLM plan substance review",
    ),
    review_spec: bool = typer.Option(
        False,
        "--review-spec",
        help="Run LLM spec quality review",
    ),
    all_reviewers: bool = typer.Option(
        False,
        "--all-reviewers",
        "-R",
        help="Use all configured reviewers",
    ),
    review_model: str | None = typer.Option(
        None,
        "--model",
        help="Override reviewer model ID",
    ),
    no_review: bool = typer.Option(
        False,
        "--no-review",
        help="Skip automatic review (for hook integration)",
    ),
    sdk_isolated: bool = typer.Option(
        False,
        "--sdk-isolated",
        help="Run Layer 3 SDK-isolated tests (pytest -m level_3b)",
    ),
    # @spec FR-006: state-files validator subcommand — .specs/features/013-state-model-identity-resolution/spec.md#fr-006  # noqa: E501
    state_files: bool = typer.Option(
        False,
        "--state-files",
        help=(
            "Validate the shared frontmatter schema across pipeline.md, progress.md, "
            "ship.md, preflight.md (Chantier 4 / Feature 013)"
        ),
    ),
    migrate: bool = typer.Option(
        False,
        "--migrate",
        help=(
            "Used with --state-files: add the canonical frontmatter to legacy state "
            "files in place. Existing keys are preserved (no overwrite); body content "
            "is preserved verbatim. Inferences: feature_slug from path, dates from git "
            "log (filesystem mtime fallback), current_state from body markers (Done by "
            "default for historical files)."
        ),
    ),
) -> None:
    """Validate .specs/ files structurally.

    Args:
        path: Explicit file or directory to validate (auto-detects .specs/ if omitted).
        staged: Validate only git-staged files.
        output_format: Output format (compact, full, or json).
        warn_only: Don't exit with error code.
        score_only: Show only validation scores per file.
        list_excluded: List excluded files and exit.
        fix: Run Pass 1 mechanical auto-fixes.
        smart: Enable Pass 2 Claude SDK fixes (not yet implemented).
        auto: Skip confirmation prompts.
        dry_run: Show fixes without applying them.
        coherence: Run Layer 2 coherence validation.
        coherence_only: Run only Layer 2 coherence checks (skip Layer 1).
        rules: Specific coherence rules to run (e.g., R1,R2).
        wave_num: Only run rules up to this wave.
        ignore_rules: Rules to ignore (e.g., R3.2,R5.1).
        strict: Block on coherence errors.
        no_suppress: Disable suppress_if_creating.
        semantic: Run Layer 4 semantic validation.
        scorecard: Run scorecard only.
        contradiction_only: Run contradiction detection only.
        reindex: Reindex embeddings.
        mutate: Run mutation testing.
        experimental_multi_model: Enable multi-model consensus.
        plan_review: Run LLM-based plan substance review.
        review_spec: Run LLM-based spec quality review.
        all_reviewers: Use all configured reviewer models.
        review_model: Override reviewer model ID.
        no_review: Skip automatic review (for hook integration).
        sdk_isolated: Run Layer 3 SDK-isolated tests via pytest subprocess.

    Returns:
        None (exits via typer.Exit with appropriate code).

    Raises:
        typer.Exit: On validation failure or configuration error.
    """
    # Mutual exclusion
    if staged and path:
        typer.echo("Error: --staged and PATH are mutually exclusive", err=True)
        raise typer.Exit(1)

    # @spec FR-006: state-files validation — .specs/features/013-state-model-identity-resolution/spec.md#fr-006  # noqa: E501
    if state_files:
        from .state_files import migrate_state_files, validate_state_files

        specs_root = _require_specs_root(Path(path) if path else None)

        if migrate:
            mig_report = migrate_state_files(specs_root)
            typer.echo(
                f"Migrated {mig_report.files_checked} state file(s): "
                f"{mig_report.added_count} added, "
                f"{mig_report.completed_count} completed, "
                f"{mig_report.already_compliant_count} already compliant."
            )
            for outcome in mig_report.outcomes:
                if outcome.action != "already_compliant":
                    typer.echo(f"  {outcome}")
            # Re-validate after migration to confirm 0 violations
            sf_report = validate_state_files(specs_root)
            if sf_report.ok:
                typer.echo(
                    f"OK: post-migration re-validation confirms "
                    f"{sf_report.files_checked} file(s) compliant."
                )
                raise typer.Exit(0)
            typer.echo(
                f"WARN: {len(sf_report.violations)} violation(s) remain after migration "
                f"(some files could not be auto-migrated):",
                err=True,
            )
            for violation in sf_report.violations:
                typer.echo(f"  {violation}", err=True)
            raise typer.Exit(0 if warn_only else 1)

        sf_report = validate_state_files(specs_root)
        if sf_report.ok:
            typer.echo(
                f"OK: {sf_report.files_checked} state file(s) checked, no schema violation."
            )
            raise typer.Exit(0)
        typer.echo(
            f"FAIL: {len(sf_report.violations)} schema violation(s) "
            f"across {sf_report.files_checked} state file(s):",
            err=True,
        )
        for violation in sf_report.violations:
            typer.echo(f"  {violation}", err=True)
        raise typer.Exit(0 if warn_only else 1)

    # @spec FR-001: --sdk-isolated flag routing — .specs/features/002-layer-3-cli-surface/spec.md#fr-001  # noqa: E501
    if sdk_isolated:
        import importlib.util
        import os

        from .exceptions import SdkDependencyError, SdkTestRunError
        from .sdk_test_runner import SdkTestRunner

        # @spec FR-002: SDK dependency check — .specs/features/002-layer-3-cli-surface/spec.md#fr-002  # noqa: E501
        if importlib.util.find_spec("claude_agent_sdk") is None:
            typer.echo(str(SdkDependencyError()), err=True)
            raise typer.Exit(1)

        # @spec FR-003: API key warning — .specs/features/002-layer-3-cli-surface/spec.md#fr-003
        if os.environ.get("ANTHROPIC_API_KEY") is None:
            typer.echo(
                "Warning: ANTHROPIC_API_KEY not set"
                " — level_3b tests will be skipped by pytest.mark.skipif",
                err=True,
            )

        specs_root_sdk = _require_specs_root(Path(path) if path else None)
        project_root = specs_root_sdk.parent
        feature_slug = _resolve_feature_slug(
            Path(path) if path else None,
            specs_root_sdk,
        )
        budget_usd = float(os.environ.get("LIVESPEC_TEST_BUDGET_USD", "25.0"))

        try:
            sdk_result = SdkTestRunner(project_root).run(feature_slug, budget_usd)
        except SdkTestRunError as exc:
            typer.echo(f"Error: {exc}", err=True)
            raise typer.Exit(1)  # noqa: B904

        # @spec FR-005: Exit code mapping — .specs/features/002-layer-3-cli-surface/spec.md#fr-005
        if sdk_result.exit_code == 5:
            typer.echo(
                "Warning: no level_3b tests collected"
                " — check the feature slug or marker configuration",
                err=True,
            )
            raise typer.Exit(0)

        # @spec FR-008: JSON output — .specs/features/002-layer-3-cli-surface/spec.md#fr-008
        if output_format == "json":
            _output_sdk_result_json(sdk_result)

        exit_code = 0 if sdk_result.exit_code == 0 else 1
        raise typer.Exit(exit_code)

    # Layer 4 — LLM-dependent features

    # @spec FR-001: CLI flag routing — .specs/features/001-auto-llm-review/spec.md#fr-001
    if review_spec:
        from .llm_provider import is_available
        from .orchestrator import run_spec_review
        from .semantic.config import load_semantic_config

        if not is_available():
            typer.echo(
                "Error: No LLM provider configured.\n"
                "Create ~/.config/livespec/provider.py with a call_llm() function.\n"
                "See examples/provider-cchub.py for a template.",
                err=True,
            )
            raise typer.Exit(1)

        target_path = Path(path) if path else None
        specs_root_for_review = _require_specs_root(target_path)
        sem_config = load_semantic_config(specs_root_for_review)
        models = [review_model] if review_model else (sem_config.review_reviewers or None)
        feature_filter = _resolve_feature_filter(
            target_path,
            specs_root_for_review,
        )

        spec_review_result = run_spec_review(
            specs_root_for_review,
            models=models,
            all_reviewers=all_reviewers,
            confidence_threshold=sem_config.review_confidence_threshold,
            feature_filter=feature_filter,
        )

        # @spec FR-008: JSON output — .specs/features/001-auto-llm-review/spec.md#fr-008
        if output_format == "json":
            _output_review_json(spec_review_result.reviews, spec_review_result.errors)
            has_blocking = any(
                f.severity.value == "ERROR"
                for e in spec_review_result.reviews
                for f in e.result.findings
            )
            raise typer.Exit(1 if (strict and has_blocking) or spec_review_result.errors else 0)

        has_blocking = _display_review_findings(
            spec_review_result.reviews,
            spec_review_result.errors,
            review_type="Spec",
            sem_config=sem_config,
        )

        # @spec FR-007: Exit code logic — .specs/features/001-auto-llm-review/spec.md#fr-007
        raise typer.Exit(1 if strict and has_blocking else 0)

    # @spec FR-005: Plan review CLI alias — .specs/features/001-auto-llm-review/spec.md#fr-005
    if plan_review:
        from .llm_provider import is_available
        from .orchestrator import run_plan_review
        from .semantic.config import load_semantic_config

        if not is_available():
            typer.echo(
                "Error: No LLM provider configured.\n"
                "Create ~/.config/livespec/provider.py with a call_llm() function.\n"
                "See examples/provider-cchub.py for a template.",
                err=True,
            )
            raise typer.Exit(1)

        target_path = Path(path) if path else None
        specs_root_for_review = _require_specs_root(target_path)
        sem_config = load_semantic_config(specs_root_for_review)
        models = [review_model] if review_model else (sem_config.review_reviewers or None)
        feature_filter = _resolve_feature_filter(
            target_path,
            specs_root_for_review,
        )

        review_result = run_plan_review(
            specs_root_for_review,
            models=models,
            all_reviewers=all_reviewers,
            confidence_threshold=sem_config.review_confidence_threshold,
            feature_filter=feature_filter,
        )

        if output_format == "json":
            _output_review_json(review_result.reviews, review_result.errors)
            has_blocking = any(
                f.severity.value == "ERROR"
                for e in review_result.reviews
                for f in e.result.findings
            )
            raise typer.Exit(1 if (strict and has_blocking) or review_result.errors else 0)

        has_blocking = _display_review_findings(
            review_result.reviews,
            review_result.errors,
            review_type="Plan",
            sem_config=sem_config,
        )

        raise typer.Exit(0 if warn_only else (1 if (strict and has_blocking) else 0))

    if contradiction_only:
        from .llm_provider import is_available
        from .orchestrator import run_contradiction_check

        if not is_available():
            typer.echo(
                "Error: No LLM provider configured.\n"
                "Create ~/.config/livespec/provider.py with a call_llm() function.\n"
                "See examples/provider-cchub.py for a template.",
                err=True,
            )
            raise typer.Exit(1)

        specs_root_for_l4 = _require_specs_root(Path(path) if path else None)
        check_result = run_contradiction_check(specs_root_for_l4)

        typer.echo(f"Contradiction check: {check_result.pairs_count} pairs compared", err=True)
        for entry in check_result.contradictions:
            typer.echo(
                f"  [{entry.result.severity.value}] "
                f"{entry.assertion_a.source_file} x {entry.assertion_b.source_file}: "
                f"{entry.result.explanation}",
                err=True,
            )
        typer.echo(f"\n{len(check_result.contradictions)} contradiction(s) found.", err=True)
        raise typer.Exit(1 if check_result.contradictions else 0)

    if reindex:
        typer.echo("Embedding reindex requires OpenAI API (not yet integrated).", err=True)
        raise typer.Exit(0)
    if mutate:
        typer.echo(
            "Mutation testing: run `pytest tests/ -k mutation` for available tests.",
            err=True,
        )
        raise typer.Exit(0)
    if experimental_multi_model:
        typer.echo("Multi-model validation is experimental and not yet integrated.", err=True)
        raise typer.Exit(0)

    # Pass 2 stub
    if smart:
        typer.echo(
            "Error: Pass 2 (Claude SDK) not implemented in this release. Remove --smart flag.",
            err=True,
        )
        raise typer.Exit(1)

    # Resolve paths
    target = Path(path) if path else None
    specs_root = _require_specs_root(target)
    config = load_config(specs_root)

    paths = [target] if target else None
    results, excluded = validate_all(specs_root, config, paths=paths, staged_only=staged)

    # List excluded
    if list_excluded:
        report_excluded(excluded)
        raise typer.Exit(0)

    # Fix mode
    if fix:
        actions = fix_all(results, specs_root, config, dry_run=dry_run)
        if actions:
            typer.echo(f"\nAuto-fix Pass 1 {'(dry-run)' if dry_run else ''}:", err=True)
            for action in actions:
                rel = (
                    action.file.relative_to(specs_root.parent)
                    if specs_root.parent in action.file.parents
                    else action.file.name
                )
                typer.echo(f"  {rel}: {action.description}", err=True)

            if not dry_run:
                # Re-validate after fixes
                results, excluded = validate_all(
                    specs_root,
                    config,
                    paths=paths,
                    staged_only=staged,
                )
        else:
            typer.echo("\nAuto-fix: nothing to fix.", err=True)

    # Output Layer 1 results (skip if coherence-only or scorecard-only)
    if not coherence_only and not (scorecard and not semantic):
        if score_only:
            report_score_only(results, specs_root)
        else:
            json_output = report(
                results,
                excluded,
                output_format=output_format,
                specs_root=specs_root,
            )
            if json_output:
                typer.echo(json_output)

    # Layer 2 coherence validation
    coherence_result = None
    if coherence or coherence_only:
        from .coherence.report import report_coherence
        from .coherence.rule_engine import run_coherence

        rule_id_list = rules.split(",") if rules else None
        ignore_list = ignore_rules.split(",") if ignore_rules else None

        coherence_result = run_coherence(
            specs_root,
            rule_ids=rule_id_list,
            wave=wave_num,
            ignore=ignore_list,
            no_suppress=no_suppress,
            strict=strict,
        )

        if output_format == "json":
            json_out = report_coherence(coherence_result, output_format="json")
            if json_out:
                typer.echo(json_out)
        else:
            report_coherence(coherence_result, output_format=output_format)

    # Layer 4 scorecard
    if scorecard or semantic:
        from .coherence.graph_builder import build_graph
        from .semantic.report import report_scorecard
        from .semantic.scorecard import score_project

        graph = build_graph(specs_root)
        project_score = score_project(graph.features, specs_root)

        if output_format == "json":
            json_out = report_scorecard(project_score, output_format="json")
            if json_out:
                typer.echo(json_out)
        else:
            report_scorecard(project_score, output_format="compact")

    # Exit code
    has_errors = any(r.has_errors for r in results) if not coherence_only else False
    has_warnings = any(r.has_warnings for r in results) if not coherence_only else False

    if coherence_result:
        if coherence_result.has_errors:
            has_errors = True
        if strict and coherence_result.warnings:
            has_errors = True

    if warn_only:
        raise typer.Exit(0)

    if has_errors:
        raise typer.Exit(1)

    if config.block_on == "warning" and has_warnings:
        raise typer.Exit(1)

    raise typer.Exit(0)


@app.command(name="install-hook")
def install_hook(
    target_dir: str = typer.Option(".", "--target-dir", "-t", help="Target project directory"),
) -> None:
    """Install the pre-commit hook in a project.

    Args:
        target_dir: Target project directory containing .git (default: current directory).

    Raises:
        typer.Exit: If the directory is not a git repository or hook installation fails.
    """
    target = Path(target_dir).resolve()
    hooks_dir = target / ".git" / "hooks"

    if not hooks_dir.exists():
        typer.echo(f"Error: {hooks_dir} does not exist. Is this a git repository?", err=True)
        raise typer.Exit(1)

    # Find our hook source
    hook_src = Path(__file__).parent / "hooks" / "pre-commit-hook"
    if not hook_src.exists():
        typer.echo(f"Error: hook source not found at {hook_src}", err=True)
        raise typer.Exit(1)

    hook_dst = hooks_dir / "pre-commit"

    if hook_dst.exists():
        typer.echo(f"Warning: {hook_dst} already exists. Appending LiveSpec hook.", err=True)
        with open(hook_dst, "a") as f:
            f.write("\n\n# --- LiveSpec validation hook ---\n")
            f.write(hook_src.read_text())
    else:
        shutil.copy2(hook_src, hook_dst)
        hook_dst.chmod(0o755)

    typer.echo(f"LiveSpec pre-commit hook installed in {hook_dst}")


if __name__ == "__main__":
    app()
