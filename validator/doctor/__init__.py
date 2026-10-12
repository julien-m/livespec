"""Project health audit package for ``livespec doctor``."""

from __future__ import annotations

from .runtime_scan import run_doctor

__all__ = ["run_doctor"]
