# LiveSpec traceability anchors
# @spec(FR-008)
# @spec(FR-009)

"""CLI surface for deterministic registry finalization (``livespec finalize``).

Subcommands:
* ``apply``: write the four end-of-command registry updates atomically and
  idempotently under ``.specs/.LOCK``. Exit ``0|9``.
* ``verify``: read-only coherence re-check (R1/R4/R6 scoped to the feature)
  with a JSON receipt. Exit ``0|10``.

Naming note (Feature 048 vs 058): ``finalize`` governs *registry* artifacts
(changelogs, README, spec status); run-artifact verification against
``expectations.md`` is a separate surface.
"""

from __future__ import annotations

import datetime as _dt
import json
from pathlib import Path
from typing import Annotated

import typer

from validator.cli_commands._common import require_specs_root
from validator.cli_exit_codes import (
    EXIT_FINALIZE_BLOCKED,
    EXIT_FINALIZE_VERIFY_FAIL,
    EXIT_OK,
)
from validator.finalize import (
    ApplyRequest,
    FinalizeError,
    apply_finalization,
    verify_finalization,
)
from validator.locks import LockAcquisitionError, LockRetryPolicy, WriteHashMismatchError

# Step ids used in canonical BLOCKED lines (anti-drift-block §2): step 1 is
# lock acquisition, step 2 is the hash-checked registry write sequence.
_APPLY_LOCK_STEP = 1
_APPLY_WRITE_STEP = 2

finalize_app = typer.Typer(
    name="finalize",
    help=(
        "Deterministic end-of-command registry finalization "
        "(feature changelog, global changelog, README, spec status)."
    ),
    no_args_is_help=True,
)


def register(app: typer.Typer) -> None:
    """Register the ``finalize`` command group on ``app``.

    # @spec FR-009: typer surface via the register(app) pattern
    #   — .specs/features/058-deterministic-finalization/spec.md#fr-009
    """
    app.add_typer(finalize_app, name="finalize")


def _default_run_id() -> str:
    return _dt.datetime.now(tz=_dt.UTC).strftime("%Y%m%dT%H%M%SZ")


def _feature_number(feature_slug: str) -> str:
    return feature_slug.split("-", 1)[0]


@finalize_app.command("apply")
def apply_command(
    feature: Annotated[
        str,
        typer.Option("--feature", help="Feature slug under .specs/features/."),
    ],
    command: Annotated[
        str,
        typer.Option("--command", help="Finalizing command (e.g. spec-specify)."),
    ],
    entry_file: Annotated[
        Path,
        typer.Option("--entry-file", help="Feature changelog entry body (date-free)."),
    ],
    status: Annotated[
        str | None,
        typer.Option("--status", help="New spec status; omitted = skip the status target."),
    ] = None,
    summary: Annotated[
        str | None,
        typer.Option("--summary", help="Global changelog line (date-free); derived if omitted."),
    ] = None,
    retry: Annotated[
        bool,
        typer.Option("--retry/--no-retry", help="Opt-in backoff+jitter lock retry (~45s)."),
    ] = False,
    run_id: Annotated[
        str | None,
        typer.Option("--run-id", help="Receipt run id (default: UTC timestamp)."),
    ] = None,
    json_out: Annotated[bool, typer.Option("--json", help="Emit a JSON envelope.")] = False,
) -> None:
    """Apply all registry updates atomically and idempotently under lock.

    # @spec FR-001: apply CLI flags surface
    #   — .specs/features/058-deterministic-finalization/spec.md#fr-001
    """
    project_root = require_specs_root()
    try:
        entry_body = entry_file.read_text(encoding="utf-8").strip()
    except OSError as exc:
        typer.echo(f"Error: cannot read --entry-file: {exc}", err=True)
        raise typer.Exit(EXIT_FINALIZE_BLOCKED) from exc
    first_line = entry_body.splitlines()[0] if entry_body else ""
    # Default summary derives from the entry so both stay date-free (FR-002).
    global_summary = summary or f"[Feature {_feature_number(feature)}] {first_line}"
    request = ApplyRequest(
        feature_slug=feature,
        command=command,
        status=status,
        entry_body=entry_body,
        global_summary=global_summary,
        run_id=run_id or _default_run_id(),
    )
    try:
        result = apply_finalization(
            project_root,
            request,
            retry_policy=LockRetryPolicy() if retry else None,
        )
    except LockAcquisitionError as exc:
        # @spec FR-008: canonical BLOCKED policy_blocked on lock timeout
        #   — .specs/features/058-deterministic-finalization/spec.md#fr-008
        typer.echo(f"BLOCKED at step {_APPLY_LOCK_STEP} - policy_blocked - {exc}", err=True)
        raise typer.Exit(EXIT_FINALIZE_BLOCKED) from exc
    except (FinalizeError, WriteHashMismatchError) as exc:
        subtype = exc.subtype if isinstance(exc, FinalizeError) else "state_invalid"
        typer.echo(f"BLOCKED at step {_APPLY_WRITE_STEP} - {subtype} - {exc}", err=True)
        raise typer.Exit(EXIT_FINALIZE_BLOCKED) from exc
    if json_out:
        typer.echo(
            json.dumps(
                {
                    "outcome": result.outcome,
                    "receipt_path": str(result.receipt_path),
                    "written": list(result.written),
                    "skipped": list(result.skipped),
                },
                indent=2,
            )
        )
    else:
        typer.echo(str(result.receipt_path))
        typer.echo(f"finalize apply: {result.outcome} ({len(result.written)} written)", err=True)
    raise typer.Exit(EXIT_OK)


@finalize_app.command("verify")
def verify_command(
    feature: Annotated[
        str,
        typer.Option("--feature", help="Feature slug under .specs/features/."),
    ],
    command: Annotated[
        str | None,
        typer.Option("--command", help="Require finalize markers for this command."),
    ] = None,
    run_id: Annotated[
        str | None,
        typer.Option("--run-id", help="Receipt run id (default: UTC timestamp)."),
    ] = None,
    json_out: Annotated[bool, typer.Option("--json", help="Emit a JSON envelope.")] = False,
) -> None:
    """Re-check registry coherence (read-only) and emit a JSON receipt.

    # @spec FR-004: verify CLI flags surface
    #   — .specs/features/058-deterministic-finalization/spec.md#fr-004
    """
    project_root = require_specs_root()
    result = verify_finalization(
        project_root,
        feature,
        expected_command=command,
        run_id=run_id or _default_run_id(),
    )
    if json_out:
        typer.echo(
            json.dumps(
                {
                    "verdict": result.verdict,
                    "receipt_path": str(result.receipt_path),
                    "violations": [
                        {"rule_id": violation.rule_id, "message": violation.message}
                        for violation in result.violations
                    ],
                },
                indent=2,
            )
        )
    else:
        typer.echo(str(result.receipt_path))
    if result.verdict != "PASS":
        for violation in result.violations:
            typer.echo(f"{violation.rule_id}: {violation.message}", err=True)
        typer.echo(f"finalize verify: FAIL ({len(result.violations)} violations)", err=True)
        raise typer.Exit(EXIT_FINALIZE_VERIFY_FAIL)
    typer.echo("finalize verify: PASS", err=True)
    raise typer.Exit(EXIT_OK)


__all__ = ["apply_command", "finalize_app", "register", "verify_command"]
