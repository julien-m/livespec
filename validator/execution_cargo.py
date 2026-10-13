"""Entry point of the trusted Cargo runner, executed as `python -I execution_cargo.py`.

Modes:
    drive --profdata P --cov C -- cargo test ...   build, run and publish evidence
    hook <config> <sha256> <binary> [args...]      Cargo target runner for one binary

Runs in isolated mode, so only the LiveSpec checkout containing this file is put on
`sys.path`; the project's working directory can never shadow runner modules.
"""

# @spec FR-001: Trusted Cargo runner entry
#   — .specs/features/085-cargo-execution-runner/spec.md#fr-001

from __future__ import annotations

import sys
from pathlib import Path


def main(argv: list[str]) -> int:
    """Dispatch to the driver or the per-binary hook."""
    if argv[:1] == ["drive"]:
        from validator.execution_cargo_driver import drive

        return drive(argv[1:])
    if argv[:1] == ["hook"]:
        from validator.execution_cargo_hook import hook

        return hook(argv[1:])
    print("usage: execution_cargo.py drive|hook ...", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    raise SystemExit(main(sys.argv[1:]))
