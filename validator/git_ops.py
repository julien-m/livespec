"""Git operations CLI for LiveSpec — branch, stage, merge, delete, status."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import typer

git_app = typer.Typer(name="git", help="Git operations for LiveSpec pipelines.")


@git_app.command()
def branch(
    name: str = typer.Argument(..., help="Branch name to create and check out"),
) -> None:
    """Create and check out a new git branch.

    Exit codes: 0 = success, 1 = failure (branch already exists or other error).
    """
    result = subprocess.run(
        ["git", "checkout", "-b", name],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        typer.echo(result.stderr.strip(), err=True)
        raise typer.Exit(1)
    typer.echo(f"Created and checked out branch: {name}")
    raise typer.Exit(0)


@git_app.command()
def stage(
    feature: str = typer.Option(
        ..., "--feature", help="Feature directory name (e.g. 001-my-feature)"
    ),
) -> None:
    """Stage feature files plus roadmap.md and changelog.md.

    Exit codes: 0 = success, 1 = failure.
    """
    feature_path = Path(".specs") / "features" / feature

    # Stage the feature directory (required — fail if missing)
    result = subprocess.run(
        ["git", "add", str(feature_path)],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        typer.echo(result.stderr.strip(), err=True)
        raise typer.Exit(1)

    # Stage optional shared files — ignore errors if they don't exist
    for optional in [".specs/roadmap.md", ".specs/changelog.md"]:
        subprocess.run(
            ["git", "add", optional],
            check=False,
            capture_output=True,
            text=True,
        )

    # Count staged files
    count_result = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        check=False,
        capture_output=True,
        text=True,
    )
    staged_files = [f for f in count_result.stdout.splitlines() if f.strip()]
    typer.echo(f"{len(staged_files)} files staged")
    raise typer.Exit(0)


@git_app.command()
def merge(
    branch_name: str = typer.Argument(..., help="Branch to merge into current branch"),
    no_ff: bool = typer.Option(False, "--no-ff", help="Disable fast-forward merge"),
) -> None:
    """Merge a branch into the current branch.

    Exit codes: 0 = clean merge, 1 = generic failure, 2 = merge conflict (abort attempted).
    """
    cmd = ["git", "merge", branch_name]
    if no_ff:
        cmd.append("--no-ff")

    result = subprocess.run(cmd, check=False, capture_output=True, text=True)

    combined = (result.stdout or "") + (result.stderr or "")
    if "CONFLICT" in combined:
        # Attempt abort — whether it succeeds or fails, always exit 2
        abort_result = subprocess.run(
            ["git", "merge", "--abort"],
            check=False,
            capture_output=True,
            text=True,
        )
        if abort_result.returncode != 0:
            typer.echo(f"Abort failed: {abort_result.stderr.strip()}", err=True)
        else:
            typer.echo("Merge aborted.", err=True)

        # Extract conflicting files from stdout
        conflicts = [
            line.split("Merge conflict in ")[-1].strip()
            for line in result.stdout.splitlines()
            if "Merge conflict in" in line
        ]
        typer.echo(f"Conflict: {', '.join(conflicts) if conflicts else 'unknown'}")
        raise typer.Exit(2)

    if result.returncode != 0:
        typer.echo(result.stderr.strip(), err=True)
        raise typer.Exit(1)

    typer.echo(f"Merged {branch_name}")
    raise typer.Exit(0)


@git_app.command()
def delete(
    branch_name: str = typer.Argument(..., help="Branch to delete"),
    force: bool = typer.Option(False, "--force", help="Force delete even if not fully merged"),
) -> None:
    """Delete a git branch.

    Exit codes: 0 = success, 1 = branch not found or generic error, 2 = not fully merged (without --force).
    """
    flag = "-D" if force else "-d"
    result = subprocess.run(
        ["git", "branch", flag, branch_name],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        stderr = result.stderr or ""
        if "not fully merged" in stderr:
            typer.echo(stderr.strip(), err=True)
            raise typer.Exit(2)
        typer.echo(stderr.strip(), err=True)
        raise typer.Exit(1)

    typer.echo(f"Deleted branch: {branch_name}")
    raise typer.Exit(0)


@git_app.command(name="status")
def git_status() -> None:
    """Show current git status as JSON.

    Stdout: JSON with keys: branch, staged, ahead, behind.
    Exit codes: 0 = success, 1 = not a git repo.
    """
    # Check we're in a git repo
    check = subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"],
        check=False,
        capture_output=True,
        text=True,
    )
    if check.returncode != 0:
        typer.echo("Error: not a git repository", err=True)
        raise typer.Exit(1)

    # Current branch
    branch_result = subprocess.run(
        ["git", "branch", "--show-current"],
        check=False,
        capture_output=True,
        text=True,
    )
    current_branch = branch_result.stdout.strip()

    # Staged files
    staged_result = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        check=False,
        capture_output=True,
        text=True,
    )
    staged = [f for f in staged_result.stdout.splitlines() if f.strip()]

    # Ahead/behind relative to upstream (if any)
    ahead = 0
    behind = 0
    upstream_result = subprocess.run(
        ["git", "rev-list", "--left-right", "--count", "HEAD...@{upstream}"],
        check=False,
        capture_output=True,
        text=True,
    )
    if upstream_result.returncode == 0 and upstream_result.stdout.strip():
        parts = upstream_result.stdout.strip().split()
        if len(parts) == 2:
            try:
                ahead = int(parts[0])
                behind = int(parts[1])
            except ValueError:
                pass

    output = {
        "branch": current_branch,
        "staged": staged,
        "ahead": ahead,
        "behind": behind,
    }
    typer.echo(json.dumps(output))
    raise typer.Exit(0)
