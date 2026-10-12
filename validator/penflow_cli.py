"""Locate the Penflow CLI installed alongside the running LiveSpec interpreter."""

from __future__ import annotations

import os
import shutil
import sys
from collections.abc import Callable
from pathlib import Path

PENFLOW_CLI_ENV = "LIVESPEC_PENFLOW_BIN"
_PENFLOW = "penflow"

Which = Callable[[str], str | None]


# @spec FR-007: Validate canonical input before review
# .specs/features/077-penflow-cumulative-verdict-consumer/spec.md#fr-007
def resolve_penflow_cli(which: Which | None = None) -> str | None:
    """Return the Penflow executable LiveSpec must call, or ``None`` when absent.

    Resolution order: an explicit ``LIVESPEC_PENFLOW_BIN`` override (never followed by a
    fallback), then ``penflow`` in the bin directory of ``sys.executable`` (the pinned CLI
    installed in the same environment works without an activated venv), then ``PATH``.

    Args:
        which: Executable lookup, ``shutil.which`` at call time when omitted.

    Returns:
        Absolute or PATH-resolved executable, or ``None`` when no candidate is runnable.
    """
    lookup = which or shutil.which
    override = os.environ.get(PENFLOW_CLI_ENV, "").strip()
    if override:
        return lookup(override)
    # Do not resolve symlinks: a venv's bin/python links to the base interpreter.
    sibling = lookup(str(Path(sys.executable).parent / _PENFLOW))
    return sibling or lookup(_PENFLOW)


def penflow_cli_missing(code: str) -> str:
    """Prefix ``code`` with the locations searched, for an actionable rejection."""
    override = os.environ.get(PENFLOW_CLI_ENV, "").strip()
    if override:
        return f"{code}: {PENFLOW_CLI_ENV}={override} is not an executable Penflow CLI"
    return (
        f"{code}: penflow not found in {Path(sys.executable).parent} or on PATH; "
        f"install the pinned Penflow CLI in the LiveSpec environment or set {PENFLOW_CLI_ENV}"
    )
