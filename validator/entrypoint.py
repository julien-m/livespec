"""Dispatch package-installed commands through the machine's runtime shim."""

from __future__ import annotations

import os
import sys
from pathlib import Path


# @spec FR-004: Package launcher honors pins
#   — .specs/features/083-pinned-runtime-isolation/spec.md#fr-004
def main() -> int:
    """Replace this process with the installed shim, preserving its interpreter.

    Returns:
        Shim resolution exit 3 if the shim is missing, recursive or cannot execute.
        Otherwise exec transfers arguments, cwd, environment and standard streams.

    The package CLI remains directly available through ``python -m validator.cli``
    for explicit bootstrap and recovery. Never import it as an implicit fallback:
    that would bypass project pins and the shim's bound Python environment.
    """
    home = Path(os.environ.get("LIVESPEC_HOME") or Path.home() / ".livespec").expanduser()
    shim = home / "bin" / "livespec"
    try:
        if not shim.is_file():
            raise OSError(f"runtime shim is missing: {shim}")
        if shim.resolve() == Path(sys.argv[0]).resolve():
            raise OSError(f"package launcher replaced the runtime shim: {shim}")
        # Execute the file, rather than importing its code with this package's Python.
        # The installed shim owns runtime selection and bound-interpreter re-execution.
        os.execv(str(shim), [str(shim), *sys.argv[1:]])
    except (OSError, RuntimeError) as exc:
        sys.stderr.write(
            f"livespec-shim: {exc}; bootstrap or repair from the LiveSpec checkout: "
            "python -m validator.cli runtime install --source <livespec repo> "
            "--ref <commit> [--home <runtime home>]\n"
        )
        return 3
