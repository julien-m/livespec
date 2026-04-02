"""CLI entry point for LiveSpec validator."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path
from typing import Optional

import typer

from .config import load_config
from .engine import validate_all
from .fixer import fix_all
from .reporter import report, report_excluded, report_score_only

app = typer.Typer(name="livespec", help="LiveSpec structural validator")


def _find_specs_root(start: Path | None = None) -> Path:
    """Find the .specs/ directory starting from the given path or cwd."""
    search = start or Path.cwd()
    if search.is_file():
        search = search.parent

    # Check if path is inside .specs/
    for parent in [search, *search.parents]:
        if parent.name == ".specs":
            return parent
        specs_dir = parent / ".specs"
        if specs_dir.is_dir():
            return specs_dir

    typer.echo("Error: .specs/ directory not found", err=True)
    raise typer.Exit(1)


@app.command()
def validate(
    path: Optional[str] = typer.Argument(None, help="File or directory to validate"),
    staged: bool = typer.Option(False, "--staged", help="Validate git staged files only"),
    format: str = typer.Option("compact", "--format", "-f", help="Output format: compact, full, json"),
    warn_only: bool = typer.Option(False, "--warn-only", help="Don't exit with error code"),
    score_only: bool = typer.Option(False, "--score-only", help="Show scores only"),
    fix: bool = typer.Option(False, "--fix", help="Apply Pass 1 mechanical fixes"),
    smart: bool = typer.Option(False, "--smart", help="Apply Pass 2 Claude SDK fixes (not yet implemented)"),
    auto: bool = typer.Option(False, "--auto", help="Skip confirmation prompts"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview fixes without modifying files"),
    list_excluded: bool = typer.Option(False, "--list-excluded", help="Show excluded files"),
) -> None:
    """Validate .specs/ files structurally."""
    # Mutual exclusion
    if staged and path:
        typer.echo("Error: --staged and PATH are mutually exclusive", err=True)
        raise typer.Exit(1)

    # Pass 2 stub
    if smart:
        typer.echo(
            "Error: Pass 2 (Claude SDK) not implemented in this release. Remove --smart flag.",
            err=True,
        )
        raise typer.Exit(1)

    # Resolve paths
    target = Path(path) if path else None
    specs_root = _find_specs_root(target)
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
                rel = action.file.relative_to(specs_root.parent) if specs_root.parent in action.file.parents else action.file.name
                typer.echo(f"  {rel}: {action.description}", err=True)

            if not dry_run:
                # Re-validate after fixes
                results, excluded = validate_all(specs_root, config, paths=paths, staged_only=staged)
        else:
            typer.echo("\nAuto-fix: nothing to fix.", err=True)

    # Output
    if score_only:
        report_score_only(results, specs_root)
    else:
        json_output = report(results, excluded, format=format, specs_root=specs_root)
        if json_output:
            typer.echo(json_output)

    # Exit code
    has_errors = any(r.has_errors for r in results)
    has_warnings = any(r.has_warnings for r in results)

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
    """Install the pre-commit hook in a project."""
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
