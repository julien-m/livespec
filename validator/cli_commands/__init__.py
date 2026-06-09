# LiveSpec traceability anchors
# @spec(FR-002)
# @spec(FR-003)
# @spec(FR-005)

"""Unified CLI subcommand implementations (Feature 035).

Each module in this package implements one top-level ``livespec`` subcommand
introduced by Feature 035. The Typer entry points are registered from
``validator/cli.py``; the ``register(app)`` function in each module wires the
callback to a typer app instance so the surface stays declarative and
auto-discoverable.
"""

from __future__ import annotations

import typer

from . import (
    command_audit_cmd,
    coverage_cmd,
    design_alignment_cmd,
    doctor_cmd,
    drivers_cmd,
    journey_cmd,
    migrate_cmd,
    mutation_cmd,
    penflow_contract_cmd,
    preflight_cmd,
    test_cmd,
    ui_runner_cmd,
    utility_cmd,
    visual_gate_cmd,
)


def register_unified_commands(app: typer.Typer) -> None:
    """Register the unified subcommands on ``app``.

    Args:
        app: Top-level ``livespec`` Typer application.
    """
    test_cmd.register(app)
    coverage_cmd.register(app)
    design_alignment_cmd.register(app)
    doctor_cmd.register(app)
    drivers_cmd.register(app)
    journey_cmd.register(app)
    mutation_cmd.register(app)
    penflow_contract_cmd.register(app)
    preflight_cmd.register(app)
    ui_runner_cmd.register(app)
    command_audit_cmd.register(app)
    utility_cmd.register(app)
    visual_gate_cmd.register(app)
    migrate_cmd.register(app)


__all__ = ["register_unified_commands"]
