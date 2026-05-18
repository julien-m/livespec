"""Typer subcommand: ``livespec init test-config``.

Feature 026 surface used by ``/spec-init`` Phase C and by
``/spec-refresh-conventions`` to (re)generate per-stack test configuration.
"""

# @spec FR-005: Integrate generate_test_config into /spec-init pipeline.
# @spec AC-002: Unsupported stack -> note + exit 0 without writing files.
# @spec AC-007: Print summary listing generated files.
# @spec AC-006: Reused by spec-refresh-conventions for the testing domain.

from __future__ import annotations

from pathlib import Path

import typer

from .registry import DriverRegistry
from .test_config import (
    DEFAULT_THRESHOLD,
    generate_test_config,
    materialize_files,
    pick_primary_driver,
    update_conventions_testing_domain,
)

init_app = typer.Typer(name="init", help="LiveSpec init helpers")


@init_app.command("test-config")
def test_config_command(
    threshold: float = typer.Option(
        DEFAULT_THRESHOLD,
        "--threshold",
        help="Coverage gate threshold percentage (0 < t <= 100).",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Overwrite existing skip_if_exists files (e.g. CI workflow).",
    ),
    project_root: str | None = typer.Option(
        None,
        "--project-root",
        help="Project root (defaults to current working directory).",
    ),
    refresh_conventions_only: bool = typer.Option(
        False,
        "--refresh-conventions-only",
        help=(
            "Only update .conventions/index.md testing domain "
            "(no coverage config or CI workflow written)."
        ),
    ),
) -> None:
    """Generate stack-specific test configuration files.

    Args:
        threshold: Coverage threshold percentage applied to the runner config.
        force: Overwrite existing files that normally use ``skip_if_exists``.
        project_root: Repository root, defaults to ``Path.cwd()``.
        refresh_conventions_only: Skip writing config + CI files. Used by
            ``/spec-refresh-conventions`` to bring conventions back in sync
            after a stack change without touching project config.

    Side Effects:
        Writes config files, the CI workflow, and patches the conventions
        index. Emits a summary block on stdout.
    """
    root = Path(project_root) if project_root else Path.cwd()
    if not root.is_dir():
        typer.echo(f"Error: project root not found: {root}", err=True)
        raise typer.Exit(2)

    registry = DriverRegistry(root)
    matching = registry.discover()
    primary = pick_primary_driver(matching, root)

    if primary is None:
        # AC-002: graceful skip — do not block /spec-init.
        typer.echo(
            "Test config not generated — stack not supported. "
            "Use `livespec spec.driver --new <stack>` to add a custom driver.",
        )
        raise typer.Exit(0)

    try:
        plan = generate_test_config(primary, root, threshold=threshold)
    except ValueError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(2)  # noqa: B904

    if not refresh_conventions_only:
        outcomes = materialize_files(plan.files, root, force=force)
        for outcome in outcomes:
            line = f"  {outcome.action:>8}  {outcome.path}"
            if outcome.reason:
                line += f"   ({outcome.reason})"
            typer.echo(line)

    conventions_index = root / ".conventions" / "index.md"
    if update_conventions_testing_domain(plan, primary, conventions_index):
        typer.echo(f"  updated  {conventions_index.relative_to(root)}")
    else:
        typer.echo(
            "  note     .conventions/index.md not found — testing domain skipped.",
        )

    typer.echo(
        f"\nDone. Stack: {primary.name} | Runner: {plan.runner} "
        f"| Threshold: {plan.threshold:g}% | Snapshots: {plan.snapshot_lib}",
    )
    typer.echo("Next: run `livespec spec-test` to validate the generated config.")
    raise typer.Exit(0)
