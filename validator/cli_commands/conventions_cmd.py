# @spec(FR-006)

# LiveSpec traceability anchors
# @spec(FR-009)

"""Conventions CLI commands for LiveSpec."""

from __future__ import annotations

import json
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import typer

from ..conventions_ast.ars_rules import project_has_ars_inventory, validate_ars_rule_registry
from ..conventions_ast.corpus import build_corpus_manifest
from ..conventions_ast.source_decisions import (
    build_rule_decision_manifest,
    validate_rule_decision_manifest,
)
from ..conventions_ast.taxonomy import advisory_rules, unsupported_rules
from ..conventions_diffguard import (
    base_hash_snapshot,
    changed_protected_conventions_paths,
    compare_base_hashes,
    git_changed_paths,
    supervisor_conventions_gate,
)
from ..conventions_feature_scope import FeatureScopeError, resolve_feature_scope
from ..conventions_gate import verify_conventions
from ..conventions_gate_types import GateBlocker, GateResult, GateVerdict
from ..conventions_gates import (
    GatesInitMode,
    gates_path,
    generate_conventions_gates,
    load_conventions_gates,
)
from ..conventions_receipt import write_conventions_receipt
from ..conventions_rules import RulebookStaleError, compile_conventions_rulebook
from ..llm_provider import LLMProviderNotConfigured
from .conventions_scaffold import (
    is_web_ui_stack,
    render_conventions_index,
    render_conventions_manifest,
    scaffold_linter_configs,
)

REPO_OPTION = typer.Option(Path("."), "--repo", help="Project repository root.")
JSON_OPTION = typer.Option(False, "--json", help="Emit JSON.")
FULL_OPTION = typer.Option(False, "--full", help="Regenerate even when present.")
FEATURE_OPTION = typer.Option(None, "--feature", help="Feature or goal slug for receipt evidence.")
RUN_ID_OPTION = typer.Option(None, "--run-id", help="Receipt run id.")
REPO_FEATURE_SCOPE = "repo"
FEATURE_SLUG_PATTERN = re.compile(r"^\d{3}(?:\.\d+)?-[a-z0-9][a-z0-9-]*$")
RUN_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,79}$")
AST_MODE_OPTION = typer.Option(
    None,
    "--ast-mode",
    help=(
        "AST rollout selector. Default (no flag) writes schema v2 enforce-by-default "
        "gates; 'observe' records findings without blocking; 'off' opts out to legacy "
        "schema v1 (no AST enforcement)."
    ),
)
WORKER_RECEIPT_OPTION = typer.Option(
    None,
    "--worker-receipt",
    help="Optional worker-provided conventions receipt JSON.",
)

conventions_app = typer.Typer(name="conventions", help="Manage LiveSpec conventions.")
gates_app = typer.Typer(name="gates", help="Manage conventions gates.")
conventions_app.add_typer(gates_app, name="gates")


@conventions_app.command("refresh")
def refresh_conventions_command(repo: Path = REPO_OPTION, full: bool = FULL_OPTION) -> None:
    """Refresh the project conventions bundle."""
    repo_root = repo.resolve()
    stack_path = repo_root / ".specs" / "stacks" / "_default.md"
    if not stack_path.is_file():
        typer.echo("Error: .specs/stacks/_default.md not found", err=True)
        raise typer.Exit(2)
    conventions_dir = repo_root / ".conventions"
    index_path = conventions_dir / "index.md"
    manifest_path = conventions_dir / "manifest.yaml"
    if index_path.is_file() and manifest_path.is_file() and not full:
        typer.echo("conventions already present")
        raise typer.Exit(0)

    conventions_dir.mkdir(parents=True, exist_ok=True)
    stack_text = stack_path.read_text(encoding="utf-8").lower()
    domains = ["code"]
    if is_web_ui_stack(stack_text):
        domains += ["design-tokens", "design-components", "design-views", "design-quality"]
    index_path.write_text(render_conventions_index(repo_root.name, domains), encoding="utf-8")
    manifest_path.write_text(render_conventions_manifest(domains, stack_text), encoding="utf-8")
    typer.echo("conventions refreshed")
    typer.echo(f"  updated  {index_path.relative_to(repo_root)}")
    typer.echo(f"  updated  {manifest_path.relative_to(repo_root)}")
    raise typer.Exit(0)


@gates_app.command("init")
def conventions_gates_init_command(
    repo: Path = REPO_OPTION,
    force: bool = typer.Option(False, "--force", help="Overwrite existing gates file."),
    ast_mode: GatesInitMode | None = AST_MODE_OPTION,
) -> None:
    """Generate `.specs/conventions-gates.yaml` from project sources."""
    try:
        path = generate_conventions_gates(repo.resolve(), force=force, ast_mode=ast_mode)
    except FileExistsError:
        typer.echo("conventions gates already present", err=True)
        raise typer.Exit(1) from None
    except FileNotFoundError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(2) from exc
    typer.echo(f"conventions gates written: {path}")
    raise typer.Exit(0)


@conventions_app.command("verify")
def conventions_verify_command(
    repo: Path = REPO_OPTION,
    json_out: bool = JSON_OPTION,
    report: bool = typer.Option(False, "--report", help="Write debt report artifacts."),
    feature: str | None = FEATURE_OPTION,
    run_id: str | None = RUN_ID_OPTION,
) -> None:
    """Verify conventions deterministically."""
    repo_root = repo.resolve()
    try:
        validated_feature = _validate_conventions_feature(feature) if feature is not None else None
        if validated_feature is not None and run_id is not None:
            _validate_conventions_run_id(run_id)
        feature_scope = (
            resolve_feature_scope(repo_root, validated_feature)
            if validated_feature is not None and validated_feature != REPO_FEATURE_SCOPE
            else None
        )
        result = verify_conventions(repo_root, report=report, feature_scope=feature_scope)
        result = _with_rule_decision_blockers(result, repo_root)
    except (FeatureScopeError, FileNotFoundError, ValueError) as exc:
        payload: dict[str, object] = {"verdict": "BLOCKED", "blockers": [str(exc)]}
        if feature is not None:
            payload.update({"feature_slug": feature, "run_id": run_id, "receipt_path": None})
        typer.echo(
            json.dumps(payload, indent=2) if json_out else f"BLOCKED: {exc}",
            err=not json_out,
        )
        raise typer.Exit(2) from exc
    try:
        payload = _conventions_verify_payload(
            repo_root, feature=validated_feature, run_id=run_id, result=result
        )
    except ValueError as exc:
        payload = {"verdict": "BLOCKED", "blockers": [str(exc)]}
        if validated_feature is not None:
            payload.update(
                {"feature_slug": validated_feature, "run_id": run_id, "receipt_path": None}
            )
        typer.echo(
            json.dumps(payload, indent=2) if json_out else f"BLOCKED: {exc}",
            err=not json_out,
        )
        raise typer.Exit(2) from exc
    if json_out:
        typer.echo(json.dumps(payload, indent=2, sort_keys=True))
    else:
        typer.echo(f"Conventions verdict: {result.verdict.value}")
        typer.echo(f"violations: {len(result.violations)}")
        if validated_feature is not None:
            typer.echo(f"receipt: {payload['receipt_path']}")
        for blocker in result.blockers:
            typer.echo(f"BLOCKED: {blocker.message}", err=True)
    raise typer.Exit({"PASS": 0, "FAIL": 1, "BLOCKED": 2}[result.verdict.value])


def _default_conventions_run_id() -> str:
    return datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%SZ")


def _validate_conventions_run_id(run_id: str) -> str:
    if RUN_ID_PATTERN.fullmatch(run_id) is None:
        raise ValueError(f"invalid run_id: {run_id}")
    return run_id


def _validate_conventions_feature(feature: str) -> str:
    if feature == REPO_FEATURE_SCOPE:
        return feature
    if FEATURE_SLUG_PATTERN.fullmatch(feature) is None:
        raise ValueError(f"invalid feature slug: {feature}")
    return feature


def _conventions_verify_payload(
    repo_root: Path,
    *,
    feature: str | None,
    run_id: str | None,
    result: GateResult,
) -> dict[str, object]:
    payload: dict[str, object] = {**result.to_dict()}
    _lift_taxonomy_to_top_level(payload, result, repo_root)
    if feature is None:
        return payload
    effective_run_id = _validate_conventions_run_id(run_id or _default_conventions_run_id())
    receipt_path = write_conventions_receipt(
        project_root=repo_root,
        feature_slug=feature,
        run_id=effective_run_id,
        result=result,
        gates_path=gates_path(repo_root),
    )
    payload.update(
        {
            "feature_slug": feature,
            "run_id": effective_run_id,
            "receipt_path": receipt_path.relative_to(repo_root).as_posix(),
        }
    )
    return payload


def _with_rule_decision_blockers(result: GateResult, repo_root: Path) -> GateResult:
    summary = result.ast_summary or {}
    manifest = summary.get("rule_decision_manifest") or build_rule_decision_manifest(repo_root)
    ars_issues = (
        validate_ars_rule_registry(repo_root) if project_has_ars_inventory(repo_root) else []
    )
    issues = [*validate_rule_decision_manifest(cast(Any, manifest)), *ars_issues]
    if not issues:
        return result
    blockers = [
        *result.blockers,
        *[
            GateBlocker(
                "rule_decision_manifest_invalid",
                issue,
                "Fix source decisions before writing conventions evidence.",
            )
            for issue in issues
        ],
    ]
    return GateResult(
        verdict=GateVerdict.BLOCKED,
        violations=result.violations,
        blockers=blockers,
        ast_summary=result.ast_summary,
    )


def _lift_taxonomy_to_top_level(
    payload: dict[str, object],
    result: GateResult,
    repo_root: Path,
) -> None:
    """Surface advisory/unsupported taxonomy at the verify JSON top level.

    The taxonomy lives inside ``ast_summary`` (so it flows to the receipt too),
    but consumers/auditors expect ``advisory_rules``/``unsupported_rules`` at the
    document root. Absence of v2 AST gates leaves both as empty lists rather than
    missing keys, so a stable contract holds for v1 repos as well.
    """
    summary = result.ast_summary or {}
    payload["advisory_rules"] = summary.get("advisory_rules") or advisory_rules()
    payload["unsupported_rules"] = summary.get("unsupported_rules") or unsupported_rules()
    payload["source_manifest"] = summary.get("source_manifest") or build_corpus_manifest(repo_root)
    payload["rule_decision_manifest"] = summary.get(
        "rule_decision_manifest"
    ) or build_rule_decision_manifest(repo_root)


@conventions_app.command("supervisor-gate")
def conventions_supervisor_gate_command(
    repo: Path = REPO_OPTION,
    base_ref: str = typer.Option(..., "--base-ref", help="Base git ref for diff/hash guards."),
    head_ref: str = typer.Option("HEAD", "--head-ref", help="Head git ref for diff guard."),
    worker_receipt: Path | None = WORKER_RECEIPT_OPTION,
    json_out: bool = JSON_OPTION,
) -> None:
    """Run supervisor-only conventions locks before accepting pipeline output."""
    repo_root = repo.resolve()
    try:
        payload, exit_code = _build_supervisor_gate_payload(
            repo_root,
            base_ref=base_ref,
            head_ref=head_ref,
            worker_receipt=worker_receipt,
        )
    except (OSError, subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        payload = {"verdict": "BLOCKED", "reason": "supervisor_gate_error", "blockers": [str(exc)]}
        exit_code = 2
    if json_out:
        typer.echo(json.dumps(payload, indent=2, sort_keys=True))
    else:
        typer.echo(f"Conventions supervisor verdict: {payload['verdict']}")
        if payload.get("reason"):
            typer.echo(f"BLOCKED: {payload['reason']}", err=True)
    raise typer.Exit(exit_code)


def _build_supervisor_gate_payload(
    repo_root: Path,
    *,
    base_ref: str,
    head_ref: str,
    worker_receipt: Path | None,
) -> tuple[dict[str, object], int]:
    changed_paths = git_changed_paths(repo_root, base_ref=base_ref, head_ref=head_ref)
    protected_paths = changed_protected_conventions_paths(repo_root, changed_paths=changed_paths)
    if protected_paths:
        return (
            {
                "verdict": "BLOCKED",
                "reason": "gate_files_modified_in_pipeline",
                "protected_paths": protected_paths,
            },
            2,
        )
    hash_blockers = compare_base_hashes(repo_root, base_hash_snapshot(repo_root, base_ref=base_ref))
    if hash_blockers:
        return (
            {"verdict": "BLOCKED", "reason": "base_hash_mismatch", "blockers": hash_blockers},
            2,
        )
    result = supervisor_conventions_gate(
        repo_root,
        worker_receipt=_read_worker_receipt(repo_root, worker_receipt),
        run_verify=_run_supervisor_verify,
    )
    return (
        {
            "verdict": result.verdict,
            "source": result.source,
            "stale_worker_verdict": result.stale_worker_verdict,
        },
        {"PASS": 0, "FAIL": 1, "BLOCKED": 2}[result.verdict],
    )


def _read_worker_receipt(repo_root: Path, worker_receipt: Path | None) -> dict[str, object] | None:
    if worker_receipt is None:
        return None
    path = worker_receipt if worker_receipt.is_absolute() else repo_root / worker_receipt
    return json.loads(path.read_text(encoding="utf-8"))


def _run_supervisor_verify(repo_root: Path, feature_slug: str | None) -> GateResult:
    if feature_slug is None:
        return _with_rule_decision_blockers(verify_conventions(repo_root), repo_root)
    feature_scope = resolve_feature_scope(repo_root, feature_slug)
    result = verify_conventions(repo_root, feature_scope=feature_scope)
    return _with_rule_decision_blockers(result, repo_root)


@conventions_app.command("compile")
def conventions_compile_command(
    repo: Path = REPO_OPTION,
    force: bool = typer.Option(False, "--force", help="Overwrite stale rulebook."),
    json_out: bool = JSON_OPTION,
) -> None:
    """Compile a self-contained semantic conventions rulebook."""
    try:
        path = compile_conventions_rulebook(repo.resolve(), force=force)
    except RulebookStaleError as exc:
        message = f"conventions rulebook stale: {exc}. Re-run with --force after reviewing changes."
        typer.echo(
            json.dumps({"status": "stale", "error": message}, indent=2) if json_out else message
        )
        raise typer.Exit(1) from exc
    except LLMProviderNotConfigured as exc:
        _blocked("provider_not_configured", str(exc), json_out)
        raise typer.Exit(2) from exc
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
        _blocked("rulebook_error", str(exc), json_out)
        raise typer.Exit(2) from exc
    typer.echo(
        json.dumps({"status": "written", "path": str(path)}, indent=2)
        if json_out
        else f"conventions rulebook written: {path}"
    )
    raise typer.Exit(0)


@conventions_app.command("semantic")
def conventions_semantic_command(repo: Path = REPO_OPTION, json_out: bool = JSON_OPTION) -> None:
    """Run Layer 4 semantic conventions Engine C."""
    from ..conventions_engine_c import run_semantic_conventions

    try:
        result = run_semantic_conventions(repo.resolve())
    except FileNotFoundError as exc:
        _blocked("rulebook_missing", f"{exc} Run conventions compile first.", json_out)
        raise typer.Exit(2) from exc
    except ValueError as exc:
        _blocked("rulebook_invalid", str(exc), json_out)
        raise typer.Exit(2) from exc
    if json_out:
        typer.echo(json.dumps(result.model_dump(mode="json"), indent=2, sort_keys=True))
    else:
        typer.echo(f"Semantic conventions verdict: {result.verdict.value}")
        for blocker in result.blockers:
            typer.echo(f"BLOCKED: {blocker}", err=True)
    raise typer.Exit({"PASS": 0, "FAIL": 1, "BLOCKED": 2}[result.verdict.value])


@conventions_app.command("scaffold")
def conventions_scaffold_command(
    repo: Path = REPO_OPTION,
    apply: bool = typer.Option(False, "--apply", help="Write scaffold files."),
    sync_limits: bool = typer.Option(False, "--sync-limits", help="Sync managed linter limits."),
) -> None:
    """Scaffold conventions linter config."""
    repo_root = repo.resolve()
    gates = load_conventions_gates(gates_path(repo_root))
    changed = scaffold_linter_configs(repo_root, gates, apply=apply, sync_limits=sync_limits)
    typer.echo("\n".join(changed) if changed else "conventions scaffold: no changes")
    raise typer.Exit(0)


def _blocked(reason: str, blocker: str, json_out: bool) -> None:
    if json_out:
        payload = {"verdict": "BLOCKED", "reason": reason, "blockers": [blocker]}
        typer.echo(json.dumps(payload, indent=2))
    else:
        typer.echo(f"BLOCKED: {reason}: {blocker}", err=True)
