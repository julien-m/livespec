"""``livespec ui-runner`` exposes the Phase 4.5 visual dispatcher.

Client projects invoke the globally installed LiveSpec CLI rather than
importing `validator/ui_runner_dispatcher.py` from the client tree. This
module provides the `check` preflight and `dispatch` execution entry points
used by `/spec.test --visual`.
"""

# @spec FR-014: Runner-aware preflight via livespec CLI — .specs/features/037-test-multi-runner-integration/spec.md#fr-014  # noqa: E501

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Annotated, Any, TypedDict, cast

import typer
import yaml  # type: ignore[import-untyped]  # PyYAML is installed in the repo, but the stub package is not.

from validator.ui_runner_dispatcher import (
    Phase4_5Dispatcher,
    VisualPhaseResult,
    _resolve_registry,
)

CORE_RUNNERS = ("playwright", "xcuitest", "maestro")
STATUS_READY = "READY"
STATUS_BLOCKED = "BLOCKED"
STATUS_SKIPPED = "SKIP"
STATUS_OK = "OK"
STATUS_FAIL = "FAIL"


class SurfaceCheckSummary(TypedDict):
    """JSON-safe summary for one surface during `ui-runner check`."""

    id: str
    runner: str
    status: str
    note: str


class CheckPayload(TypedDict):
    """Machine-readable payload returned by `ui-runner check --json`."""

    status: str
    reason: str | None
    surfaces: list[SurfaceCheckSummary]
    registry: list[str]


class DispatchPayload(TypedDict):
    """Machine-readable payload returned by `ui-runner dispatch --json`."""

    surface_id: str
    runner: str
    screen: str
    status: str
    baseline_path: str | None
    error: str | None
    metadata: dict[str, object]


ui_runner_app = typer.Typer(
    name="ui-runner",
    help="Phase 4.5 visual dispatcher (playwright + xcuitest + maestro).",
    no_args_is_help=True,
)


def register(app: typer.Typer) -> None:
    """Register the ``ui-runner`` command group."""
    # Order matters because `ui-runner` is a top-level namespace with nested
    # subcommands, not a flat callback like `livespec test` or `preflight`.
    app.add_typer(ui_runner_app, name="ui-runner")


@ui_runner_app.command("check")
def check_command(
    project_dir: str = typer.Option(
        ".",
        "--project-dir",
        "-p",
        help="Project root (default: cwd).",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit machine-readable JSON instead of human text.",
    ),
) -> None:
    """Verify runner registry resolution and surface/tooling availability.

    Args:
        project_dir: Project root containing `.specs/surfaces.yaml`.
        json_output: Emit JSON instead of human-readable output.

    Raises:
        typer.Exit: With code 0 when ready or 2 when blocked.
    """
    project_path = Path(project_dir).resolve()
    registry = _resolve_registry()
    registry_names = [runner for runner in CORE_RUNNERS if runner in registry]

    try:
        _validate_surfaces_yaml(project_path)
    except ValueError as exc:
        _emit_check(
            json_output,
            status=STATUS_BLOCKED,
            reason=str(exc),
            surfaces=[],
            registry=registry_names,
        )
        raise typer.Exit(code=2) from exc

    dispatcher = Phase4_5Dispatcher(project_dir=project_path, feature_dir=project_path)
    surface_summaries: list[SurfaceCheckSummary] = []
    blocking_reasons: list[str] = []

    for surface in dispatcher.surfaces:
        runner_name = surface.runner
        handler_cls = registry.get(runner_name)
        if handler_cls is None:
            note = f"runner {runner_name} is not handled"
            surface_summaries.append(
                {
                    "id": surface.id,
                    "runner": runner_name,
                    "status": STATUS_BLOCKED,
                    "note": note,
                }
            )
            # Backward compatibility for Feature 037: older manifests may still
            # reference unsupported runner names, which must hard-block visual runs.
            blocking_reasons.append(f"{surface.id} ({runner_name}): {note}")
            continue

        # The protocol models instance methods only; concrete handlers are still
        # constructible from a single project path, so the CLI mirrors the dispatcher.
        handler_factory = cast(Any, handler_cls)
        handler = handler_factory((project_path / surface.path).resolve())
        if handler.detect():
            surface_summaries.append(
                {
                    "id": surface.id,
                    "runner": runner_name,
                    "status": STATUS_READY,
                    "note": "",
                }
            )
            continue

        note = handler.preflight_message() or f"{runner_name} preflight failed"
        surface_summaries.append(
            {
                "id": surface.id,
                "runner": runner_name,
                "status": STATUS_BLOCKED,
                "note": note,
            }
        )
        blocking_reasons.append(f"{surface.id} ({runner_name}): {note}")

    if blocking_reasons:
        _emit_check(
            json_output,
            status=STATUS_BLOCKED,
            reason="; ".join(blocking_reasons),
            surfaces=surface_summaries,
            registry=registry_names,
        )
        raise typer.Exit(code=2)

    _emit_check(
        json_output,
        status=STATUS_READY,
        reason=None,
        surfaces=surface_summaries,
        registry=registry_names,
    )


def _validate_surfaces_yaml(project_dir: Path) -> None:
    """Validate `.specs/surfaces.yaml` early so `check` can hard-block on parse errors.

    Args:
        project_dir: Project root that may contain `.specs/surfaces.yaml`.

    Raises:
        ValueError: If the YAML file exists but cannot be parsed or is not a mapping.
    """
    surfaces_path = project_dir / ".specs" / "surfaces.yaml"
    if not surfaces_path.exists():
        return

    try:
        parsed = yaml.safe_load(surfaces_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ValueError(f"surfaces_unparseable: {exc}") from exc

    if parsed is None:
        return
    if not isinstance(parsed, dict):
        # `surfaces.yaml` is expected to be a top-level mapping with a
        # `surfaces:` array; any other shape is treated as unparseable input.
        raise ValueError("surfaces_unparseable: expected a top-level mapping")


def _emit_check(
    json_output: bool,
    *,
    status: str,
    reason: str | None,
    surfaces: list[SurfaceCheckSummary],
    registry: list[str],
) -> None:
    """Emit the `ui-runner check` result in JSON or human form.

    Args:
        json_output: Whether to emit JSON.
        status: Top-level READY/BLOCKED result.
        reason: Aggregated blocking reason when blocked.
        surfaces: Per-surface readiness summaries.
        registry: Runner names currently wired into the CLI registry.
    """
    payload: CheckPayload = {
        "status": status,
        "reason": reason,
        "surfaces": surfaces,
        "registry": registry,
    }
    if json_output:
        typer.echo(json.dumps(payload, indent=2))
        return

    typer.echo(f"Phase 4.5 preflight: {status}")
    typer.echo(f"  Handlers: {', '.join(registry)}")
    for surface in surfaces:
        line = (
            f"  - {surface['id']} [{surface['runner']}] -> {surface['status']}"
        )
        if surface["note"]:
            line += f" -- {surface['note']}"
        typer.echo(line)
    if reason is not None and status == STATUS_BLOCKED:
        typer.echo(f"  Reason: {reason}", err=True)


@ui_runner_app.command("dispatch")
def dispatch_command(
    screens: Annotated[
        list[str] | None,
        typer.Argument(
            help="Screen identifiers to capture/compare (one per surface x screen pair).",
        ),
    ] = None,
    project_dir: str = typer.Option(
        ".",
        "--project-dir",
        "-p",
        help="Project root (default: cwd).",
    ),
    feature_dir: str = typer.Option(
        ...,
        "--feature-dir",
        "-f",
        help="Feature directory (e.g. .specs/features/004-name/).",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit machine-readable JSON aggregated results.",
    ),
) -> None:
    """Execute the Phase 4.5 dispatcher for the supplied screens.

    Args:
        screens: Screen identifiers to capture or compare.
        project_dir: Project root containing runner assets.
        feature_dir: Feature directory for the current visual run.
        json_output: Emit JSON instead of human-readable output.

    Raises:
        typer.Exit: With code 0 on success, 1 on visual diff failure, or 2 when blocked.
    """
    if not screens:
        typer.echo("No screens provided.", err=True)
        raise typer.Exit(code=2)

    project_path = Path(project_dir).resolve()
    feature_path = Path(feature_dir).resolve()
    results = Phase4_5Dispatcher(
        project_dir=project_path,
        feature_dir=feature_path,
    ).run(screens)

    if json_output:
        typer.echo(json.dumps(_serialize_results(results), indent=2))
    else:
        for result in results:
            line = (
                f"  - {result.surface_id} [{result.runner}] "
                f"{result.screen}: {_normalize_dispatch_status(result.status)}"
            )
            if result.error:
                line += f" -- {result.error}"
            typer.echo(line)

    exit_code = _dispatch_exit_code(results)
    raise typer.Exit(code=exit_code)


@ui_runner_app.command("inspect")
def inspect_command(
    xcresult: str = typer.Argument(
        ...,
        help="Path to the .xcresult bundle produced by xcodebuild test.",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit machine-readable JSON.",
    ),
    patch: str | None = typer.Option(
        None,
        "--patch",
        help=(
            "Path to a Swift UI test file. When set, inspect rewrites the "
            "tapFirstAvailable/tapAnyTab candidate lists with the labels "
            "actually found on each screen (auto-fix navigation TODOs)."
        ),
    ),
) -> None:
    """Extract accessibility trees from a test run and report per-screen elements.

    The Swift template attaches `<screen>.tree.txt` to every snapshot. This
    command pulls them out of the .xcresult bundle, parses interactive
    elements (buttons, tabs, cells, statictexts), and prints a per-screen
    inventory. Use `--patch <file>` to auto-rewrite the Swift candidates so
    you don't have to chase accessibilityIdentifier mismatches manually.

    Args:
        xcresult: Path to .xcresult bundle.
        json_output: Emit JSON instead of human text.
        patch: When provided, rewrite the Swift test file's tap candidates.

    Raises:
        typer.Exit: With code 0 on success, 2 on parse errors.
    """
    from validator.ui_runner_inspect import (
        extract_screen_trees,
        parse_tree_elements,
        rewrite_swift_candidates,
    )

    bundle = Path(xcresult).resolve()
    if not bundle.exists():
        typer.echo(f"BLOCKED: .xcresult not found at {bundle}", err=True)
        raise typer.Exit(code=2)

    trees = extract_screen_trees(bundle)
    if not trees:
        typer.echo(
            "No <screen>.tree.txt attachments found. Make sure the Swift test "
            "uses the snapshot() helper from livespec/ui-runners/xcuitest-template "
            "(or run `livespec ui-runner scaffold --target ios --force`).",
            err=True,
        )
        raise typer.Exit(code=2)

    inventories: dict[str, dict[str, list[str]]] = {}
    for screen, tree_text in trees.items():
        inventories[screen] = parse_tree_elements(tree_text)

    if patch:
        target = Path(patch).resolve()
        if not target.exists():
            typer.echo(f"BLOCKED: Swift file not found at {target}", err=True)
            raise typer.Exit(code=2)
        changed = rewrite_swift_candidates(target, inventories)
        typer.echo(f"Patched {changed} test method(s) in {target.name}")

    if json_output:
        typer.echo(json.dumps(inventories, indent=2))
        return

    for screen, inv in inventories.items():
        typer.echo(f"\n=== {screen} ===")
        for kind in ("tabs", "buttons", "cells", "statictexts"):
            items = inv.get(kind, [])
            if items:
                typer.echo(f"  {kind}: {', '.join(items[:8])}")


@ui_runner_app.command("converge")
def converge_command(
    screens: Annotated[
        list[str] | None,
        typer.Argument(help="Screen identifiers to capture across iterations."),
    ] = None,
    project_dir: str = typer.Option(".", "--project-dir", "-p", help="Project root."),
    feature_dir: str = typer.Option(
        ...,
        "--feature-dir",
        "-f",
        help="Feature directory (e.g. .specs/features/001-name/).",
    ),
    max_iterations: int = typer.Option(
        5,
        "--max-iterations",
        "-n",
        help="Stop after this many dispatch+patch cycles even if not converged.",
    ),
) -> None:
    """Loop dispatch + inspect --patch until the Swift candidate lists stabilise.

    The first run usually captures the wrong screen because the auto-generated
    `tapFirstAvailable` candidate lists are placeholders. `inspect --patch`
    injects the real labels XCUITest saw, so the next run navigates one level
    deeper. Repeat until `--patch` reports zero changes — that's convergence.

    Args:
        screens: Screen identifiers (same as dispatch).
        project_dir: Project root.
        feature_dir: Feature directory.
        max_iterations: Hard stop to avoid infinite loops on unreachable screens.

    Raises:
        typer.Exit: With code 0 on convergence, 1 if max iterations reached
            without stabilising, 2 on dispatch failure.
    """
    if not screens:
        typer.echo("No screens provided.", err=True)
        raise typer.Exit(code=2)

    project_path = Path(project_dir).resolve()
    feature_path = Path(feature_dir).resolve()
    bundles_dir = project_path / ".specs" / ".test-bundles"
    bundles_dir.mkdir(parents=True, exist_ok=True)

    # Lockfile prevents two `converge` instances from clobbering each other's
    # .xcresult bundles. The lock holds a stale-detection pid + start time so a
    # crashed prior run can be reaped without a manual `rm`.
    import os
    import time
    lock_file = bundles_dir / "converge.lock"
    if lock_file.exists():
        try:
            stale_pid = int(lock_file.read_text(encoding="utf-8").split(":", 1)[0])
        except (ValueError, OSError):
            stale_pid = -1
        if stale_pid > 0:
            try:
                os.kill(stale_pid, 0)
            except ProcessLookupError:
                stale_pid = -1
            else:
                typer.echo(
                    f"BLOCKED: another `livespec ui-runner converge` is already "
                    f"running (pid {stale_pid}). Wait for it to finish or kill it.",
                    err=True,
                )
                raise typer.Exit(code=2)
        if stale_pid <= 0:
            typer.echo(
                "Removing stale converge.lock from a previous crashed run.",
                err=True,
            )
            lock_file.unlink(missing_ok=True)
    lock_file.write_text(f"{os.getpid()}:{int(time.time())}", encoding="utf-8")

    try:
        _converge_loop(
            project_path=project_path,
            feature_path=feature_path,
            bundles_dir=bundles_dir,
            screens=screens,
            max_iterations=max_iterations,
        )
    finally:
        lock_file.unlink(missing_ok=True)


def _converge_loop(
    *,
    project_path: Path,
    feature_path: Path,
    bundles_dir: Path,
    screens: list[str],
    max_iterations: int,
) -> None:
    """Inner converge loop, extracted so the outer command can hold a lockfile."""
    import sys

    from validator.ui_runner_dispatcher import Phase4_5Dispatcher
    from validator.ui_runner_inspect import (
        extract_screen_trees,
        parse_tree_elements,
        rewrite_swift_candidates,
    )

    for iteration in range(1, max_iterations + 1):
        typer.echo(f"\n--- Iteration {iteration}/{max_iterations} ---")
        sys.stdout.flush()
        typer.echo(
            f"  Dispatching {len(screens)} screen(s) "
            f"(first iter can take 5-15 min on cold build)..."
        )
        sys.stdout.flush()

        # 1. Dispatch
        results = Phase4_5Dispatcher(
            project_dir=project_path,
            feature_dir=feature_path,
        ).run(screens)
        for r in results:
            typer.echo(
                f"  [{r.surface_id}] {r.screen}: "
                f"{_normalize_dispatch_status(r.status)}"
                + (f" — {r.error[:80]}" if r.error else "")
            )
        sys.stdout.flush()

        # 2. Patch each surface's Swift file from its persisted .xcresult
        total_patched = 0
        if not bundles_dir.exists():
            typer.echo("  No .xcresult bundles produced — nothing to inspect.")
            raise typer.Exit(code=2)

        for bundle in bundles_dir.glob("*.xcresult"):
            test_target = bundle.stem  # e.g. "STRAPTUITests"
            swift_dir = project_path / test_target
            if not swift_dir.exists():
                typer.echo(
                    f"  ~ {test_target}: no matching Swift directory at {swift_dir}"
                )
                continue
            swift_files = list(swift_dir.glob("*.swift"))
            if not swift_files:
                typer.echo(f"  ~ {test_target}: no .swift files in {swift_dir}")
                continue

            trees = extract_screen_trees(bundle)
            if not trees:
                typer.echo(f"  ~ {test_target}: no <screen>.tree.txt attachments")
                continue
            inventories = {
                screen: parse_tree_elements(text) for screen, text in trees.items()
            }
            for swift_file in swift_files:
                changed = rewrite_swift_candidates(swift_file, inventories)
                total_patched += changed
                typer.echo(
                    f"  → {test_target}/{swift_file.name}: patched {changed} method(s)"
                )

        if total_patched == 0:
            typer.echo(
                f"\n✓ Converged after {iteration} iteration(s) — "
                f"no more candidates to inject."
            )
            raise typer.Exit(code=0)

    typer.echo(
        f"\n✗ Did not converge after {max_iterations} iterations. "
        "Some screens may be unreachable via current navigation; "
        "inspect the .specs/.test-bundles/*.xcresult bundles manually.",
        err=True,
    )
    raise typer.Exit(code=1)


@ui_runner_app.command("scaffold")
def scaffold_command(
    target: str = typer.Option(
        "ios",
        "--target",
        "-t",
        help="Scaffold target: 'ios' (XCUITest) or 'android' (Maestro).",
    ),
    project_dir: str = typer.Option(
        ".",
        "--project-dir",
        "-p",
        help="Project root (default: cwd).",
    ),
    out_dir: str | None = typer.Option(
        None,
        "--out",
        "-o",
        help=(
            "Override destination directory (defaults: <App>UITests/ for ios, "
            ".specs/maestro/ for android)."
        ),
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Overwrite existing files.",
    ),
) -> None:
    """Copy LiveSpec UI runner test templates into the current project.

    Bridges the gap between `xcodebuild test` exit 0 and zero baseline emission:
    the UITest target must call XCTAttachment(screenshot:) per screen identifier.
    This command drops a working LSSampleUITests.swift into your UITests target
    that demonstrates the pattern, including launchArguments wiring.

    Args:
        target: 'ios' (XCUITest) or 'android' (Maestro flow).
        project_dir: Project root (default: cwd).
        out_dir: Override destination directory.
        force: Overwrite existing files.

    Raises:
        typer.Exit: With code 0 on success, 2 on missing template/destination conflicts.
    """
    project_path = Path(project_dir).resolve()
    target_lower = target.lower()

    # Locate the template directory inside the LiveSpec install. The CLI runs
    # from the global install, so we resolve relative to this module.
    livespec_root = Path(__file__).resolve().parents[2]
    template_name = "xcuitest" if target_lower == "ios" else "maestro"
    template_dir = (
        livespec_root / "livespec" / "ui-runners" / f"{template_name}-template"
    )

    if not template_dir.exists():
        typer.echo(
            f"BLOCKED: template not found at {template_dir}. "
            f"Re-run /spec.migrate or reinstall LiveSpec.",
            err=True,
        )
        raise typer.Exit(code=2)

    # Resolve destination
    if out_dir is not None:
        dest = (project_path / out_dir).resolve()
    elif target_lower == "ios":
        # Try common UITests directory naming
        candidates = list(project_path.glob("*UITests"))
        dest = candidates[0] if candidates else project_path / "UITests"
    else:
        dest = project_path / ".specs" / "maestro"

    dest.mkdir(parents=True, exist_ok=True)

    copied: list[str] = []
    skipped: list[str] = []
    for src in template_dir.iterdir():
        if src.is_dir():
            continue
        target_file = dest / src.name
        if target_file.exists() and not force:
            skipped.append(str(target_file.relative_to(project_path)))
            continue
        target_file.write_bytes(src.read_bytes())
        copied.append(str(target_file.relative_to(project_path)))

    typer.echo(f"Scaffolded {target_lower} runner template into {dest.relative_to(project_path)}/")
    for path in copied:
        typer.echo(f"  + {path}")
    for path in skipped:
        typer.echo(f"  ~ {path} (already exists, use --force to overwrite)", err=True)

    if target_lower == "ios" and copied:
        typer.echo(
            "\nNext: add LSSampleUITests.swift to your UITests target in Xcode "
            "(File > Add Files to \"<project>\"...), share the test scheme "
            "(Product > Scheme > Manage Schemes > tick 'Shared'), then re-run "
            "`livespec ui-runner dispatch`."
        )


def _serialize_results(results: list[VisualPhaseResult]) -> list[DispatchPayload]:
    """Convert dispatcher dataclasses into JSON-safe dictionaries.

    Args:
        results: Dispatcher results to serialize.

    Returns:
        JSON-safe payload entries with stringified paths and normalized statuses.
    """
    payload: list[DispatchPayload] = []
    for result in results:
        row = asdict(result)
        payload.append(
            {
                "surface_id": str(row["surface_id"]),
                "runner": str(row["runner"]),
                "screen": str(row["screen"]),
                "status": _normalize_dispatch_status(str(row["status"])),
                "baseline_path": (
                    str(result.baseline_path) if result.baseline_path is not None else None
                ),
                "error": result.error,
                "metadata": dict(result.metadata),
            }
        )
    return payload


def _normalize_dispatch_status(status: str) -> str:
    """Map dispatcher-internal lowercase statuses to CLI-facing values.

    Args:
        status: Raw dispatcher result status.

    Returns:
        Uppercase status suitable for CLI output.
    """
    normalized = status.lower()
    if normalized == "ok":
        return STATUS_OK
    if normalized == "fail":
        return STATUS_FAIL
    if normalized == "blocked":
        return STATUS_BLOCKED
    if normalized == "skipped":
        return STATUS_SKIPPED
    return normalized.upper()


def _dispatch_exit_code(results: list[VisualPhaseResult]) -> int:
    """Return the CLI exit code for a dispatch result set.

    Args:
        results: Aggregated dispatcher results.

    Returns:
        `2` when any surface is blocked, `1` on a diff failure, otherwise `0`.
    """
    # The CLI preserves the dispatcher severity order: tooling blocks are a
    # harder failure than visual diffs, so they win when both appear.
    if any(result.status.lower() == "blocked" for result in results):
        return 2
    if any(result.status.lower() == "fail" for result in results):
        return 1
    return 0


__all__ = ["register", "ui_runner_app"]
